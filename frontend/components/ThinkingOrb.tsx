import React, { useEffect, useRef } from "react";

interface ThinkingOrbCanvasProps {
  size?: number; // Target diameter in px (e.g. 62px)
  rotationSpeedSeconds?: number; // Full 360 rotation time in seconds
  className?: string;
}

interface Point3D {
  theta: number; // latitude angle
  phi: number; // meridian longitude angle
}

/**
 * ThinkingOrbCanvas
 * 3D rotating volumetric sphere composed of vertical curved dotted meridians.
 * Features realistic 3D perspective projection, axial tilt, depth-based opacity,
 * and top/front lighting gradients matching the reference loading UI.
 */
export const ThinkingOrbCanvas: React.FC<ThinkingOrbCanvasProps> = ({
  size = 32,
  rotationSpeedSeconds = 3.0,
  className = "",
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // High DPI scaling
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    // Precompute sphere points (22 meridians × 22 points per meridian)
    const numMeridians = 22;
    const ptsPerMeridian = 22;
    const points: Point3D[] = [];

    for (let m = 0; m < numMeridians; m++) {
      const phi = (m / numMeridians) * Math.PI * 2;
      for (let p = 0; p < ptsPerMeridian; p++) {
        // Sample latitude avoiding the exact pole singularities for discrete dots
        const t = (p + 0.5) / ptsPerMeridian;
        const theta = -Math.PI * 0.44 + t * Math.PI * 0.88;
        points.push({ theta, phi });
      }
    }

    const radius = size * 0.42; // Sphere radius in logical px (~13.4px at size=32)
    const cx = size / 2;
    const cy = size / 2;
    const cameraDist = size * 2.2; // Perspective camera distance
    const tiltAngle = 0.32; // ~18.3° forward axial tilt to reveal top rim & volumetric depth
    const cosTilt = Math.cos(tiltAngle);
    const sinTilt = Math.sin(tiltAngle);

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    let animationFrameId: number;
    let startTime: number | null = null;

    const render = (now: number) => {
      if (startTime === null) startTime = now;
      const elapsed = (now - startTime) / 1000;
      // Continuous rotation angle around Y axis
      const rotAngle = (elapsed / rotationSpeedSeconds) * Math.PI * 2;

      ctx.clearRect(0, 0, size, size);

      // Project all points and sort by depth (back to front) for accurate 3D occlusion
      interface RenderPoint {
        projX: number;
        projY: number;
        z2: number;
        y2: number;
        dotRadius: number;
        opacity: number;
        color: string;
      }

      const projectedPoints: RenderPoint[] = [];

      for (let i = 0; i < points.length; i++) {
        const { theta, phi } = points[i];
        const rotPhi = phi + rotAngle;

        // 3D coordinates on unit sphere
        const cosTheta = Math.cos(theta);
        const sinTheta = Math.sin(theta);
        const cosPhi = Math.cos(rotPhi);
        const sinPhi = Math.sin(rotPhi);

        const x0 = radius * cosTheta * sinPhi;
        const y0 = -radius * sinTheta;
        const z0 = radius * cosTheta * cosPhi;

        // Apply forward axial tilt around X axis
        const y2 = y0 * cosTilt - z0 * sinTilt;
        const z2 = y0 * sinTilt + z0 * cosTilt;
        const x2 = x0;

        // Perspective projection
        const scale = cameraDist / (cameraDist - z2);
        const projX = cx + x2 * scale;
        const projY = cy + y2 * scale;

        // Depth and lighting normalization
        const zNorm = z2 / radius; // -1 (back) to +1 (front)
        const yFactor = (1 - y2 / radius) * 0.5; // 0 (bottom) to 1 (top)

        let opacity: number;
        let dotRadius: number;
        let color: string;

        if (zNorm > 0) {
          // Front-facing points: brighter, crisp white/light gray
          const frontFactor = zNorm; // 0 to 1
          const brightness =
            0.45 + 0.55 * frontFactor * (0.65 + 0.35 * yFactor);
          opacity = Math.min(
            0.95,
            Math.max(0.35, 0.4 + 0.6 * frontFactor * (0.7 + 0.3 * yFactor)),
          );
          dotRadius = (0.75 + 0.35 * frontFactor) * scale;
          // Soft white/light gray
          const cVal = Math.floor(220 + 35 * brightness);
          color = `rgba(${cVal}, ${cVal}, ${Math.min(255, cVal + 8)}, ${opacity.toFixed(3)})`;
        } else {
          // Rear points: progressively dimmer, darker gray
          const rearFactor = 1 + zNorm; // 0 to 1
          opacity = Math.max(0.08, Math.min(0.25, 0.08 + 0.15 * rearFactor));
          dotRadius = (0.5 + 0.2 * rearFactor) * scale;
          color = `rgba(148, 163, 184, ${opacity.toFixed(3)})`;
        }

        projectedPoints.push({
          projX,
          projY,
          z2,
          y2,
          dotRadius,
          opacity,
          color,
        });
      }

      // Sort points back-to-front
      projectedPoints.sort((a, b) => a.z2 - b.z2);

      // Draw all particles
      for (let i = 0; i < projectedPoints.length; i++) {
        const pt = projectedPoints[i];
        ctx.beginPath();
        ctx.arc(
          pt.projX,
          pt.projY,
          Math.max(0.45, pt.dotRadius),
          0,
          Math.PI * 2,
        );
        ctx.fillStyle = pt.color;
        ctx.fill();
      }

      if (!reducedMotion) animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [size, rotationSpeedSeconds]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ width: `${size}px`, height: `${size}px` }}
      className={`shrink-0 block ${className}`}
    />
  );
};
