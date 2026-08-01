import ttnn

class GemmaRMSNorm:
    def __init__(self, device, weight, eps=1e-6, rms_norm_add_unit_offset=False):
        self.device = device
        self.eps = eps
        self.rms_norm_add_unit_offset = rms_norm_add_unit_offset
        self.weight = weight

    def __call__(self, x):
        x_sq = ttnn.square(x)
        mean_sq = ttnn.mean(x_sq, dim=-1, keepdim=True)
        mean_sq_eps = ttnn.add(mean_sq, self.eps)
        rsqrt = ttnn.rsqrt(mean_sq_eps)
        x_normed = ttnn.mul(x, rsqrt)
        
        if self.rms_norm_add_unit_offset:
            weight_plus_one = ttnn.add(self.weight, 1.0)
            return ttnn.mul(x_normed, weight_plus_one)
        else:
            return ttnn.mul(x_normed, self.weight)

class GemmaEmbedding:
    def __init__(self, device, weight, embed_scale=False, hidden_size=None):
        self.device = device
        self.weight = weight
        self.embed_scale = embed_scale
        self.hidden_size = hidden_size

    def __call__(self, x):
        embedded = ttnn.embedding(x, self.weight)
        if self.embed_scale and self.hidden_size is not None:
            scale = self.hidden_size ** 0.5
            embedded = ttnn.mul(embedded, scale)
        # Reshape to 4D: (batch_size, 1, seq_len, hidden_size)
        shape = list(x.shape)
        embedded = ttnn.reshape(embedded, (shape[0], 1, shape[1], self.hidden_size))
        return embedded

class GemmaMLP:
    def __init__(self, device, gate_proj, up_proj, down_proj):
        self.device = device
        self.gate_proj = gate_proj
        self.up_proj = up_proj
        self.down_proj = down_proj

    def __call__(self, x):
        gate = ttnn.linear(x, self.gate_proj)
        up = ttnn.linear(x, self.up_proj)
        gate_activated = ttnn.gelu(gate)
        intermediate = ttnn.mul(gate_activated, up)
        output = ttnn.linear(intermediate, self.down_proj)
        return output

class GemmaAttention:
    def __init__(self, device, config, layer_idx, q_proj, k_proj, v_proj, o_proj):
        self.device = device
        self.config = config
        self.layer_idx = layer_idx
        self.q_proj = q_proj
        self.k_proj = k_proj
        self.v_proj = v_proj
        self.o_proj = o_proj
        
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config["num_kv_heads"]
        self.head_dim = config["head_dim"]
        self.hidden_size = config["hidden_size"]
        self.sliding_window = config.get("sliding_window", None)
        self.sliding_window_pattern = config.get("sliding_window_pattern", None)
        self.attn_logit_softcapping = config.get("attn_logit_softcapping", None)
        
        self.q_chunk = config.get("q_chunk", 32)
        self.k_chunk = config.get("k_chunk", 64)

    def __call__(self, x, position_ids, kv_cache=None, is_decode=False):
        q = ttnn.linear(x, self.q_proj)
        k = ttnn.linear(x, self.k_proj)
        v = ttnn.linear(x, self.v_proj)

        x_shape = list(x.shape)
        batch_size = x_shape[0]
        seq_len = x_shape[2]
        
        q = ttnn.reshape(q, (batch_size, seq_len, self.num_heads, self.head_dim))
        q = ttnn.transpose(q, 1, 2)
        
        k = ttnn.reshape(k, (batch_size, seq_len, self.num_kv_heads, self.head_dim))
        k = ttnn.transpose(k, 1, 2)
        
        v = ttnn.reshape(v, (batch_size, seq_len, self.num_kv_heads, self.head_dim))
        v = ttnn.transpose(v, 1, 2)

        # GQA repeat for Key/Value heads
        if self.num_heads != self.num_kv_heads:
            groups = self.num_heads // self.num_kv_heads
            k_heads = ttnn.split(k, 1, dim=1)
            v_heads = ttnn.split(v, 1, dim=1)
            
            repeated_k_heads = []
            repeated_v_heads = []
            for h in k_heads:
                for _ in range(groups):
                    repeated_k_heads.append(h)
            for h in v_heads:
                for _ in range(groups):
                    repeated_v_heads.append(h)
                    
            k = ttnn.concat(repeated_k_heads, dim=1)
            v = ttnn.concat(repeated_v_heads, dim=1)

        use_sliding_window = False
        if self.sliding_window_pattern == "alternating" and self.sliding_window is not None:
            if self.layer_idx % 2 == 0:
                use_sliding_window = True

        if is_decode:
            k_t = ttnn.transpose(k, 2, 3)
            attn_weights = ttnn.matmul(q, k_t)
            
            scale = 1.0 / (self.head_dim ** 0.5)
            attn_weights = ttnn.mul(attn_weights, scale)
            
            if self.attn_logit_softcapping is not None:
                attn_weights = ttnn.mul(attn_weights, 1.0 / self.attn_logit_softcapping)
                attn_weights = ttnn.tanh(attn_weights)
                attn_weights = ttnn.mul(attn_weights, self.attn_logit_softcapping)
                
            attn_probs = ttnn.softmax(attn_weights, dim=-1)
            context = ttnn.matmul(attn_probs, v)
        else: 
            k_t = ttnn.transpose(k, 2, 3)
            attn_weights = ttnn.matmul(q, k_t)
            
            scale = 1.0 / (self.head_dim ** 0.5)
            attn_weights = ttnn.mul(attn_weights, scale)
            
            if self.attn_logit_softcapping is not None:
                attn_weights = ttnn.mul(attn_weights, 1.0 / self.attn_logit_softcapping)
                attn_weights = ttnn.tanh(attn_weights)
                attn_weights = ttnn.mul(attn_weights, self.attn_logit_softcapping)
                
            attn_probs = ttnn.softmax(attn_weights, dim=-1)
            context = ttnn.matmul(attn_probs, v)

        context = ttnn.transpose(context, 1, 2)
        context = ttnn.reshape(context, (batch_size, 1, seq_len, self.hidden_size))
        
        output = ttnn.linear(context, self.o_proj)
        return output

class GemmaDecoderLayer:
    def __init__(self, device, config, layer_idx, weights):
        self.device = device
        self.config = config
        self.layer_idx = layer_idx
        
        self.input_layernorm = GemmaRMSNorm(
            device=device,
            weight=weights["input_layernorm_weight"],
            eps=config["rms_norm_eps"],
            rms_norm_add_unit_offset=config["rms_norm_add_unit_offset"]
        )
        self.post_attention_layernorm = GemmaRMSNorm(
            device=device,
            weight=weights["post_attention_layernorm_weight"],
            eps=config["rms_norm_eps"],
            rms_norm_add_unit_offset=config["rms_norm_add_unit_offset"]
        )
        self.pre_feedforward_layernorm = GemmaRMSNorm(
            device=device,
            weight=weights["pre_feedforward_layernorm_weight"],
            eps=config["rms_norm_eps"],
            rms_norm_add_unit_offset=config["rms_norm_add_unit_offset"]
        )
        self.post_feedforward_layernorm = GemmaRMSNorm(
            device=device,
            weight=weights["post_feedforward_layernorm_weight"],
            eps=config["rms_norm_eps"],
            rms_norm_add_unit_offset=config["rms_norm_add_unit_offset"]
        )
        
        self.self_attn = GemmaAttention(
            device=device,
            config=config,
            layer_idx=layer_idx,
            q_proj=weights["q_proj_weight"],
            k_proj=weights["k_proj_weight"],
            v_proj=weights["v_proj_weight"],
            o_proj=weights["o_proj_weight"]
        )
        
        self.mlp = GemmaMLP(
            device=device,
            gate_proj=weights["gate_proj_weight"],
            up_proj=weights["up_proj_weight"],
            down_proj=weights["down_proj_weight"]
        )

    def __call__(self, hidden_states, position_ids, kv_cache=None, is_decode=False):
        residual = hidden_states
        hidden_states = self.input_layernorm(hidden_states)
        attn_outputs = self.self_attn(
            hidden_states,
            position_ids=position_ids,
            kv_cache=kv_cache,
            is_decode=is_decode
        )
        attn_outputs = self.post_attention_layernorm(attn_outputs)
        hidden_states = ttnn.add(residual, attn_outputs)
        
        residual = hidden_states
        hidden_states = self.pre_feedforward_layernorm(hidden_states)
        mlp_outputs = self.mlp(hidden_states)
        mlp_outputs = self.post_feedforward_layernorm(mlp_outputs)
        hidden_states = ttnn.add(residual, mlp_outputs)
        
        return hidden_states

class Gemma2Model:
    def __init__(self, device, model_name, weights):
        from models.demos.tt_transformers.tt.model_config import get_model_config
        self.device = device
        self.config = get_model_config(model_name)
        
        self.embed_tokens = GemmaEmbedding(
            device=device,
            weight=weights["embed_tokens_weight"],
            embed_scale=self.config["embed_scale"],
            hidden_size=self.config["hidden_size"]
        )
        
        self.layers = []
        for i in range(self.config["num_layers"]):
            layer_weights = {
                "input_layernorm_weight": weights[f"layers.{i}.input_layernorm_weight"],
                "post_attention_layernorm_weight": weights[f"layers.{i}.post_attention_layernorm_weight"],
                "pre_feedforward_layernorm_weight": weights[f"layers.{i}.pre_feedforward_layernorm_weight"],
                "post_feedforward_layernorm_weight": weights[f"layers.{i}.post_feedforward_layernorm_weight"],
                "q_proj_weight": weights[f"layers.{i}.self_attn.q_proj_weight"],
                "k_proj_weight": weights[f"layers.{i}.self_attn.k_proj_weight"],
                "v_proj_weight": weights[f"layers.{i}.self_attn.v_proj_weight"],
                "o_proj_weight": weights[f"layers.{i}.self_attn.o_proj_weight"],
                "gate_proj_weight": weights[f"layers.{i}.mlp.gate_proj_weight"],
                "up_proj_weight": weights[f"layers.{i}.mlp.up_proj_weight"],
                "down_proj_weight": weights[f"layers.{i}.mlp.down_proj_weight"],
            }
            self.layers.append(GemmaDecoderLayer(self.device, self.config, i, layer_weights))
            
        self.norm = GemmaRMSNorm(
            device=device,
            weight=weights["norm_weight"],
            eps=self.config["rms_norm_eps"],
            rms_norm_add_unit_offset=self.config["rms_norm_add_unit_offset"]
        )
        
        self.lm_head_weight = weights["lm_head_weight"]
        self.final_logit_softcapping = self.config.get("final_logit_softcapping", None)

    def __call__(self, input_ids, position_ids, kv_caches=None, is_decode=False):
        hidden_states = self.embed_tokens(input_ids)
        
        for i, layer in enumerate(self.layers):
            kv_cache = kv_caches[i] if kv_caches is not None else None
            hidden_states = layer(
                hidden_states,
                position_ids=position_ids,
                kv_cache=kv_cache,
                is_decode=is_decode
            )
            
        hidden_states = self.norm(hidden_states)
        logits = ttnn.linear(hidden_states, self.lm_head_weight)
        
        if self.final_logit_softcapping is not None:
            logits = ttnn.mul(logits, 1.0 / self.final_logit_softcapping)
            logits = ttnn.tanh(logits)
            logits = ttnn.mul(logits, self.final_logit_softcapping)
            
        return logits
