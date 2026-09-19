"""Cosmological dynamics engine simulating FLRW metric expansion and N-body cosmic evolution."""

import math
from typing import List, Tuple
from .models import CosmologicalParameters, Particle, SimulationState


class CosmicSimulation:
    """Simulates cosmic expansion, gravitational clustering, and large-scale structure formation."""

    SPEED_OF_LIGHT_KM_S: float = 299792.458
    GRAVITATIONAL_CONSTANT_SIM: float = 43007.1
    PLUMMER_SOFTENING_MPC: float = 0.5

    def __init__(
        self,
        parameters: CosmologicalParameters = None,
        particle_count: int = 64,
        seed: int = 42,
    ) -> None:
        """Initializes the universe simulation with cosmological parameters and particle mesh."""
        self.params = parameters if parameters is not None else CosmologicalParameters()
        self.particle_count = particle_count
        self.seed = seed
        self.cosmic_time_myr = 0.0
        self.redshift = 10.0
        self.scale_factor = 1.0 / (1.0 + self.redshift)
        self.particles: List[Particle] = self._generate_initial_mesh()

    def _next_lcg(self, state: int) -> Tuple[float, int]:
        """Generates a uniform float in [0.0, 1.0) using a 32-bit linear congruential generator."""
        next_state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        normalized = float(next_state) / float(0x100000000)
        return normalized, next_state

    def _next_gaussian(self, state: int, mean: float, std_dev: float) -> Tuple[float, int]:
        """Generates a normally distributed random float using the Box-Muller transform."""
        u_val_1, state = self._next_lcg(state)
        u_val_2, state = self._next_lcg(state)
        u1_safe = max(u_val_1, 1.0e-10)
        z_score = math.sqrt(-2.0 * math.log(u1_safe)) * math.cos(2.0 * math.pi * u_val_2)
        sample = mean + z_score * std_dev
        return sample, state

    def _generate_initial_mesh(self) -> List[Particle]:
        """Generates initial 3D particle positions with primordial Gaussian perturbations."""
        state = self.seed & 0xFFFFFFFF
        box = self.params.box_size_mpc
        generated_particles: List[Particle] = []
        for idx in range(self.particle_count):
            species = "baryon" if (idx % 6 == 0) else "cdm"
            mass = 1.0e11 if species == "cdm" else 1.6e10

            u_x, state = self._next_lcg(state)
            g_x, state = self._next_gaussian(state, 0.0, 1.5)
            pos_x = (u_x * box + g_x) % box

            u_y, state = self._next_lcg(state)
            g_y, state = self._next_gaussian(state, 0.0, 1.5)
            pos_y = (u_y * box + g_y) % box

            u_z, state = self._next_lcg(state)
            g_z, state = self._next_gaussian(state, 0.0, 1.5)
            pos_z = (u_z * box + g_z) % box

            vel_x, state = self._next_gaussian(state, 0.0, 50.0)
            vel_y, state = self._next_gaussian(state, 0.0, 50.0)
            vel_z, state = self._next_gaussian(state, 0.0, 50.0)

            particle = Particle(
                particle_id=idx,
                species=species,
                mass=mass,
                position_x=pos_x,
                position_y=pos_y,
                position_z=pos_z,
                velocity_x=vel_x,
                velocity_y=vel_y,
                velocity_z=vel_z,
            )
            generated_particles.append(particle)
        return generated_particles

    def compute_hubble_parameter(self, redshift: float) -> float:
        """Computes the expansion rate H(z) at a specified redshift under the FLRW metric."""
        one_plus_z = 1.0 + redshift
        rad_term = self.params.omega_radiation * (one_plus_z ** 4)
        mat_term = self.params.omega_matter * (one_plus_z ** 3)
        curv_term = self.params.omega_curvature * (one_plus_z ** 2)
        de_term = self.params.omega_lambda
        e_z = math.sqrt(rad_term + mat_term + curv_term + de_term)
        hubble_rate = self.params.hubble_constant_h0 * e_z
        return hubble_rate

    def compute_scale_factor(self, redshift: float) -> float:
        """Computes the dimensionless cosmic scale factor a(t) for a given redshift."""
        factor = 1.0 / (1.0 + max(redshift, -0.99))
        return factor

    def compute_horizon_entropy(self, redshift: float) -> float:
        """Calculates the Bekenstein-Hawking entropy of the cosmic apparent event horizon."""
        hubble_val = self.compute_hubble_parameter(redshift)
        horizon_radius_mpc = self.SPEED_OF_LIGHT_KM_S / max(hubble_val, 1.0e-5)
        entropy_base = 2.6e122
        reference_radius_mpc = self.SPEED_OF_LIGHT_KM_S / self.params.hubble_constant_h0
        entropy_val = entropy_base * ((horizon_radius_mpc / reference_radius_mpc) ** 2)
        return entropy_val

    def compute_power_spectrum(self, wavenumber_k: float, redshift: float) -> float:
        """Calculates the linear matter power spectrum P(k, z) using Eisenstein-Hu transfer."""
        h_ratio = self.params.hubble_constant_h0 / 100.0
        gamma_eff = self.params.omega_matter * h_ratio
        wavenumber_q = wavenumber_k / max(gamma_eff, 1.0e-4)
        term_num = math.log(1.0 + 2.34 * wavenumber_q)
        term_den = 2.34 * wavenumber_q
        poly = (
            1.0
            + 3.89 * wavenumber_q
            + (16.1 * wavenumber_q) ** 2
            + (5.46 * wavenumber_q) ** 3
            + (6.71 * wavenumber_q) ** 4
        )
        transfer_func = (term_num / max(term_den, 1.0e-6)) * (poly ** -0.25)
        growth_factor = self.compute_scale_factor(redshift)
        primordial_amp = 2.1e-9 * (100.0 ** 3)
        k_term = wavenumber_k ** self.params.spectral_index_ns
        power_val = primordial_amp * k_term * (transfer_func ** 2) * (growth_factor ** 2)
        return power_val

    def compute_two_point_correlation(self, separation_r_mpc: float) -> float:
        """Evaluates the spatial two-point correlation function xi(r) for cosmic clustering."""
        r_safe = max(separation_r_mpc, 0.1)
        correlation_length = 5.0
        power_law_index = 1.77
        xi_val = (correlation_length / r_safe) ** power_law_index
        return xi_val

    def _compute_pairwise_accelerations(self) -> List[Tuple[float, float, float]]:
        """Calculates Newtonian gravitational accelerations using periodic minimum image convention."""
        box = self.params.box_size_mpc
        half_box = box / 2.0
        eps_sq = self.PLUMMER_SOFTENING_MPC ** 2
        g_const = 1.0e-7
        accelerations: List[Tuple[float, float, float]] = []

        for i, p_i in enumerate(self.particles):
            acc_x = 0.0
            acc_y = 0.0
            acc_z = 0.0
            for j, p_j in enumerate(self.particles):
                if i == j:
                    continue
                dx = p_j.position_x - p_i.position_x
                dy = p_j.position_y - p_i.position_y
                dz = p_j.position_z - p_i.position_z

                if dx > half_box:
                    dx -= box
                elif dx < -half_box:
                    dx += box

                if dy > half_box:
                    dy -= box
                elif dy < -half_box:
                    dy += box

                if dz > half_box:
                    dz -= box
                elif dz < -half_box:
                    dz += box

                dist_sq = dx * dx + dy * dy + dz * dz + eps_sq
                inv_dist_cube = 1.0 / (dist_sq * math.sqrt(dist_sq))
                force_factor = g_const * p_j.mass * inv_dist_cube
                acc_x += force_factor * dx
                acc_y += force_factor * dy
                acc_z += force_factor * dz

            accelerations.append((acc_x, acc_y, acc_z))
        return accelerations

    def compute_clustering_index(self) -> float:
        """Measures spatial clustering inhomogeneity across discretized spatial sub-volumes."""
        grid_bins = 4
        box = self.params.box_size_mpc
        bin_size = box / grid_bins
        counts = [0] * (grid_bins ** 3)

        for p in self.particles:
            bin_x = min(int(p.position_x / bin_size), grid_bins - 1)
            bin_y = min(int(p.position_y / bin_size), grid_bins - 1)
            bin_z = min(int(p.position_z / bin_size), grid_bins - 1)
            flat_idx = bin_x * (grid_bins ** 2) + bin_y * grid_bins + bin_z
            counts[flat_idx] += 1

        mean_val = float(sum(counts)) / float(len(counts))
        variance = sum((c - mean_val) ** 2 for c in counts) / float(len(counts))
        relative_dispersion = math.sqrt(variance) / max(mean_val, 1.0e-4)
        return relative_dispersion

    def step_leapfrog(self, delta_time_myr: float) -> SimulationState:
        """Advances particle positions and velocities by one symplectic leapfrog time interval."""
        box = self.params.box_size_mpc
        initial_acc = self._compute_pairwise_accelerations()

        half_dt = 0.5 * delta_time_myr
        for idx, p in enumerate(self.particles):
            p.velocity_x += initial_acc[idx][0] * half_dt
            p.velocity_y += initial_acc[idx][1] * half_dt
            p.velocity_z += initial_acc[idx][2] * half_dt

            p.position_x = (p.position_x + p.velocity_x * delta_time_myr) % box
            p.position_y = (p.position_y + p.velocity_y * delta_time_myr) % box
            p.position_z = (p.position_z + p.velocity_z * delta_time_myr) % box

        final_acc = self._compute_pairwise_accelerations()
        for idx, p in enumerate(self.particles):
            p.velocity_x += final_acc[idx][0] * half_dt
            p.velocity_y += final_acc[idx][1] * half_dt
            p.velocity_z += final_acc[idx][2] * half_dt

        self.cosmic_time_myr += delta_time_myr
        decay_factor = math.exp(-0.0002 * delta_time_myr)
        self.redshift = max(0.0, self.redshift * decay_factor)
        self.scale_factor = self.compute_scale_factor(self.redshift)

        hubble_now = self.compute_hubble_parameter(self.redshift)
        total_mass = sum(p.mass for p in self.particles)
        volume = box ** 3
        mean_density = total_mass / max(volume, 1.0)
        power_spectrum = self.compute_power_spectrum(0.1, self.redshift)
        correlation_xi = self.compute_two_point_correlation(5.0)
        clustering = self.compute_clustering_index()
        horizon_entropy = self.compute_horizon_entropy(self.redshift)

        state = SimulationState(
            scale_factor=self.scale_factor,
            redshift=self.redshift,
            cosmic_time_myr=self.cosmic_time_myr,
            hubble_parameter=hubble_now,
            particle_count=self.particle_count,
            mean_matter_density=mean_density,
            matter_power_spectrum_p_k=power_spectrum,
            two_point_correlation_xi=correlation_xi,
            clustering_index=clustering,
            horizon_entropy=horizon_entropy,
        )
        return state
