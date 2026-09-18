"""Biomechanics and kinematic rotational physics engine for backflip evaluation."""

import math
from typing import Optional
from .models import (
    BackflipAnalysis,
    BackflipPhase,
    FailureReason,
    InertialReading,
    KinematicPose,
    Vector3D,
)


class BackflipKinematicsEngine:
    """Evaluates multi-sensor inertial telemetry and skeletal kinematics for backflip detection."""

    MIN_TOTAL_ROTATION_DEG = 330.0
    MAX_TOTAL_ROTATION_DEG = 410.0
    MIN_APEX_HEIGHT_M = 0.25
    MIN_AIRTIME_SEC = 0.40
    MAX_AXIAL_DRIFT_DEG = 35.0
    MAX_LANDING_ANGLE_ERROR_DEG = 25.0
    MIN_STABILITY_PASS_SCORE = 0.70

    @classmethod
    def analyze_inertial_telemetry(cls, readings: list[InertialReading]) -> BackflipAnalysis:
        """Process time-series IMU telemetry and determine whether a backflip succeeded."""
        if not readings or len(readings) < 5:
            reasons = tuple([FailureReason.INSUFFICIENT_AIRTIME.value])
            return BackflipAnalysis(
                is_successful=False,
                peak_pitch_deg=0.0,
                total_rotation_deg=0.0,
                max_altitude_m=0.0,
                airtime_s=0.0,
                stability_score=0.0,
                detected_phase=BackflipPhase.PREPARATION,
                failure_reasons=list(reasons),
            )

        initial_altitude = readings[0].altitude_m
        max_altitude = max(r.altitude_m for r in readings)
        apex_height = max_altitude - initial_altitude

        cumulative_rotation = 0.0
        peak_pitch = 0.0
        max_axial_drift = 0.0
        inverted_reached = False
        airborne_readings: list[InertialReading] = []

        for idx, reading in enumerate(readings):
            abs_pitch = abs(reading.pitch_deg)
            peak_pitch = max(peak_pitch, abs_pitch)

            if 140.0 <= abs_pitch <= 220.0:
                inverted_reached = True

            axial_drift = max(abs(reading.roll_deg), abs(reading.yaw_deg))
            max_axial_drift = max(max_axial_drift, axial_drift)

            if reading.altitude_m > initial_altitude + 0.05:
                airborne_readings.append(reading)

            if idx > 0:
                dt_sec = (reading.timestamp_ms - readings[idx - 1].timestamp_ms) / 1000.0
                if dt_sec > 0.0:
                    delta_angle = abs(reading.gyro_pitch_rate) * dt_sec * (180.0 / math.pi)
                    cumulative_rotation += delta_angle

        airtime_sec = (
            (airborne_readings[-1].timestamp_ms - airborne_readings[0].timestamp_ms) / 1000.0
            if airborne_readings
            else (readings[-1].timestamp_ms - readings[0].timestamp_ms) / 1000.0
        )

        final_reading = readings[-1]
        landing_pitch_error = abs((abs(final_reading.pitch_deg) % 360.0))
        if landing_pitch_error > 180.0:
            landing_pitch_error = 360.0 - landing_pitch_error

        stability_score = cls._compute_stability_score(
            landing_pitch_error=landing_pitch_error,
            axial_drift=max_axial_drift,
            final_accel=final_reading.accel_vertical,
        )

        detected_reasons = cls._evaluate_failure_conditions(
            cumulative_rotation=cumulative_rotation,
            apex_height=apex_height,
            airtime_sec=airtime_sec,
            inverted_reached=inverted_reached,
            max_axial_drift=max_axial_drift,
            stability_score=stability_score,
            landing_pitch_error=landing_pitch_error,
        )

        is_success = len(detected_reasons) == 0
        final_phase = BackflipPhase.STABILIZED if is_success else BackflipPhase.LANDING

        return BackflipAnalysis(
            is_successful=is_success,
            peak_pitch_deg=round(peak_pitch, 2),
            total_rotation_deg=round(cumulative_rotation, 2),
            max_altitude_m=round(max_altitude, 3),
            airtime_s=round(airtime_sec, 3),
            stability_score=round(stability_score, 3),
            detected_phase=final_phase,
            failure_reasons=detected_reasons,
        )

    @classmethod
    def _evaluate_failure_conditions(
        cls,
        cumulative_rotation: float,
        apex_height: float,
        airtime_sec: float,
        inverted_reached: bool,
        max_axial_drift: float,
        stability_score: float,
        landing_pitch_error: float,
    ) -> list[str]:
        """Check all geometric and kinematic criteria against thresholds."""
        reasons: list[str] = []
        if cumulative_rotation < cls.MIN_TOTAL_ROTATION_DEG or cumulative_rotation > cls.MAX_TOTAL_ROTATION_DEG:
            reasons.append(FailureReason.INSUFFICIENT_ROTATION.value)
        if apex_height < cls.MIN_APEX_HEIGHT_M:
            reasons.append(FailureReason.INSUFFICIENT_HEIGHT.value)
        if airtime_sec < cls.MIN_AIRTIME_SEC:
            reasons.append(FailureReason.INSUFFICIENT_AIRTIME.value)
        if not inverted_reached:
            reasons.append(FailureReason.NO_INVERSION.value)
        if max_axial_drift > cls.MAX_AXIAL_DRIFT_DEG:
            reasons.append(FailureReason.AXIAL_DEVIATION.value)
        if stability_score < cls.MIN_STABILITY_PASS_SCORE or landing_pitch_error > cls.MAX_LANDING_ANGLE_ERROR_DEG:
            reasons.append(FailureReason.UNSTABLE_LANDING.value)
        return reasons

    @classmethod
    def analyze_skeletal_poses(cls, poses: list[KinematicPose]) -> BackflipAnalysis:
        """Process optical skeletal pose landmarks to detect body rotation and inversion."""
        if not poses or len(poses) < 5:
            reasons = tuple([FailureReason.INSUFFICIENT_AIRTIME.value])
            return BackflipAnalysis(
                is_successful=False,
                peak_pitch_deg=0.0,
                total_rotation_deg=0.0,
                max_altitude_m=0.0,
                airtime_s=0.0,
                stability_score=0.0,
                detected_phase=BackflipPhase.PREPARATION,
                failure_reasons=list(reasons),
            )

        initial_torso_y = poses[0].torso.y
        max_torso_y = max(p.torso.y for p in poses)
        apex_height = max_torso_y - initial_torso_y

        inversion_detected = False
        peak_angle = 0.0
        cumulative_angle = 0.0

        for idx, pose in enumerate(poses):
            trunk_vector = pose.head.sub(pose.pelvis)
            angle_rad = math.atan2(trunk_vector.x, trunk_vector.y)
            angle_deg = abs(angle_rad * (180.0 / math.pi))
            peak_angle = max(peak_angle, angle_deg)

            if pose.head.y < pose.pelvis.y:
                inversion_detected = True

            if idx > 0:
                prev_vector = poses[idx - 1].head.sub(poses[idx - 1].pelvis)
                dot_prod = trunk_vector.normalized().dot(prev_vector.normalized())
                clamped_dot = max(-1.0, min(1.0, dot_prod))
                delta_rad = math.acos(clamped_dot)
                cumulative_angle += delta_rad * (180.0 / math.pi)

        airtime_sec = (poses[-1].timestamp_ms - poses[0].timestamp_ms) / 1000.0
        landing_trunk = poses[-1].head.sub(poses[-1].pelvis)
        landing_deviation_deg = abs(math.atan2(landing_trunk.x, landing_trunk.y) * (180.0 / math.pi))

        stability_score = max(0.0, 1.0 - (landing_deviation_deg / 45.0))

        detected_reasons: list[str] = []
        if not inversion_detected:
            detected_reasons.append(FailureReason.NO_INVERSION.value)
        if apex_height < cls.MIN_APEX_HEIGHT_M:
            detected_reasons.append(FailureReason.INSUFFICIENT_HEIGHT.value)
        if airtime_sec < cls.MIN_AIRTIME_SEC:
            detected_reasons.append(FailureReason.INSUFFICIENT_AIRTIME.value)
        if stability_score < cls.MIN_STABILITY_PASS_SCORE:
            detected_reasons.append(FailureReason.UNSTABLE_LANDING.value)

        is_success = len(detected_reasons) == 0

        return BackflipAnalysis(
            is_successful=is_success,
            peak_pitch_deg=round(peak_angle, 2),
            total_rotation_deg=round(cumulative_angle, 2),
            max_altitude_m=round(max_torso_y, 3),
            airtime_s=round(airtime_sec, 3),
            stability_score=round(stability_score, 3),
            detected_phase=BackflipPhase.STABILIZED if is_success else BackflipPhase.LANDING,
            failure_reasons=detected_reasons,
        )

    @classmethod
    def generate_synthetic_imu_telemetry(
        cls,
        success: bool = True,
        failure_mode: Optional[FailureReason] = None,
        samples_count: int = 50,
    ) -> list[InertialReading]:
        """Generate authentic physics-derived telemetry stream for verification."""
        telemetry: list[InertialReading] = []
        total_duration_sec = 0.80

        if not success and failure_mode == FailureReason.INSUFFICIENT_AIRTIME:
            total_duration_sec = 0.25

        step_sec = total_duration_sec / float(samples_count)
        takeoff_apex_h = 0.55

        if not success and failure_mode == FailureReason.INSUFFICIENT_HEIGHT:
            takeoff_apex_h = 0.12

        target_total_rotation = 360.0
        if not success and failure_mode == FailureReason.INSUFFICIENT_ROTATION:
            target_total_rotation = 210.0

        max_roll_deviation = 4.0
        if not success and failure_mode == FailureReason.AXIAL_DEVIATION:
            max_roll_deviation = 55.0

        for i in range(samples_count):
            curr_t = float(i) * step_sec
            norm_progress = curr_t / total_duration_sec
            curr_ms = curr_t * 1000.0

            parabolic_y = 4.0 * takeoff_apex_h * norm_progress * (1.0 - norm_progress)
            altitude = 1.0 + parabolic_y

            curr_pitch = target_total_rotation * norm_progress

            omega_pitch = (target_total_rotation * (math.pi / 180.0)) / total_duration_sec
            omega_variation = math.sin(norm_progress * math.pi) * 1.5
            effective_omega = omega_pitch + omega_variation

            curr_roll = math.sin(norm_progress * math.pi * 2.0) * max_roll_deviation
            curr_yaw = math.cos(norm_progress * math.pi) * (max_roll_deviation * 0.3)

            accel_v = 9.81 + (15.0 * math.cos(norm_progress * math.pi * 2.0))
            if not success and failure_mode == FailureReason.UNSTABLE_LANDING and i > samples_count - 5:
                curr_pitch += 40.0
                curr_roll += 35.0

            reading = InertialReading(
                timestamp_ms=round(curr_ms, 2),
                pitch_deg=round(curr_pitch, 2),
                roll_deg=round(curr_roll, 2),
                yaw_deg=round(curr_yaw, 2),
                gyro_pitch_rate=round(effective_omega, 3),
                accel_vertical=round(accel_v, 2),
                altitude_m=round(altitude, 3),
            )
            telemetry.append(reading)

        return telemetry

    @classmethod
    def generate_synthetic_skeletal_poses(cls, success: bool = True) -> list[KinematicPose]:
        """Generate kinematic skeletal pose coordinates across backflip trajectory."""
        poses: list[KinematicPose] = []
        samples_count = 25
        duration_sec = 0.70
        step_sec = duration_sec / float(samples_count)

        for i in range(samples_count):
            curr_t = float(i) * step_sec
            norm_p = float(i) / float(samples_count - 1)
            angle = norm_p * 2.0 * math.pi if success else norm_p * math.pi * 0.8

            apex_y = 0.50 * math.sin(norm_p * math.pi)
            base_torso_y = 1.0 + apex_y
            torso = Vector3D(0.0, base_torso_y, 0.0)

            head_offset_x = 0.40 * math.sin(angle)
            head_offset_y = 0.40 * math.cos(angle)
            head = Vector3D(torso.x + head_offset_x, torso.y + head_offset_y, 0.0)

            pelvis_offset_x = -0.30 * math.sin(angle)
            pelvis_offset_y = -0.30 * math.cos(angle)
            pelvis = Vector3D(torso.x + pelvis_offset_x, torso.y + pelvis_offset_y, 0.0)

            ankle_l = Vector3D(pelvis.x - 0.15, pelvis.y - 0.40, -0.10)
            ankle_r = Vector3D(pelvis.x - 0.15, pelvis.y - 0.40, 0.10)

            poses.append(
                KinematicPose(
                    timestamp_ms=round(curr_t * 1000.0, 2),
                    head=head,
                    torso=torso,
                    pelvis=pelvis,
                    left_ankle=ankle_l,
                    right_ankle=ankle_r,
                )
            )

        return poses

    @staticmethod
    def _compute_stability_score(landing_pitch_error: float, axial_drift: float, final_accel: float) -> float:
        """Compute landing balance and impact dampening stability score [0.0, 1.0]."""
        pitch_factor = max(0.0, 1.0 - (landing_pitch_error / 30.0))
        drift_factor = max(0.0, 1.0 - (axial_drift / 40.0))
        accel_error = abs(final_accel - 9.81)
        accel_factor = max(0.0, 1.0 - (accel_error / 25.0))
        raw_score = (pitch_factor * 0.50) + (drift_factor * 0.30) + (accel_factor * 0.20)
        return min(1.0, max(0.0, raw_score))
