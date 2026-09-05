// File: ttnn/cpp/ttnn/operations/eltwise/unary_backward/unary_backward.cpp
@@
-    // Existing code that uses reciprocal(input)
-    auto reciprocal_input = ttnn::reciprocal(input);
+    // Compute reciprocal but guard against division by zero.
+    auto reciprocal_input = ttnn::reciprocal(input);
+    // Create a mask where input == 0
+    auto zero_mask = ttnn::eq(input, ttnn::fill(0.0f, input.get_shape()));
+    // Replace infinite values with zero where input was zero
+    reciprocal_input = ttnn::where(
+        zero_mask,
+        ttnn::fill(0.0f, reciprocal_input.get_shape()),
+        reciprocal_input
+    );
@@
-    // Previous multiplication using reciprocal_input
-    auto grad_out = ttnn::multiply(reciprocal_input, grad_fill);
+    // Multiply using the safe reciprocal
+    auto grad_out = ttnn::multiply(reciprocal_input, grad_fill);
*** End Patch