"use client";

import { useEffect, useRef } from "react";

interface GaugeProps {
  value: number;
  min: number;
  max: number;
  label: string;
  unit: string;
  color?: string;
}

export function Gauge({ 
  value, 
  min, 
  max, 
  label, 
  unit, 
  color = "#2563eb" 
}: GaugeProps) {
  const needleRef = useRef<SVGGElement>(null);
  const valueRef = useRef<SVGTextElement>(null);

  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  const angle = -90 + (percentage * 1.8);

  useEffect(() => {
    if (needleRef.current) {
      needleRef.current.style.transition = "transform 0.3s ease-out";
      needleRef.current.style.transform = `rotate(${angle}deg)`;
    }
    if (valueRef.current) {
      valueRef.current.style.transition = "opacity 0.2s ease-out";
    }
  }, [angle]);

  const getColor = () => {
    if (percentage < 30) return "#22c55e";
    if (percentage < 70) return "#eab308";
    return "#ef4444";
  };

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" className="w-40 h-24">
        <defs>
          <linearGradient id={`gradient-${label}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="50%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
        
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="12"
          strokeLinecap="round"
        />
        
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={`url(#gradient-${label})`}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${percentage * 2.51} 251`}
        />
        
        <g ref={needleRef} style={{ transform: `rotate(${angle}deg)`, transformOrigin: "100px 100px" }}>
          <line
            x1="100"
            y1="100"
            x2="100"
            y2="35"
            stroke="#1e293b"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="100" cy="100" r="8" fill="#1e293b" />
        </g>
        
        <text
          x="100"
          y="95"
          textAnchor="middle"
          className="text-xs fill-slate-500"
        >
          {min}
        </text>
        <text
          x="180"
          y="95"
          textAnchor="middle"
          className="text-xs fill-slate-500"
        >
          {max}
        </text>
        
        <text
          ref={valueRef}
          x="100"
          y="118"
          textAnchor="middle"
          className="text-sm font-bold fill-slate-800"
        >
          {value.toFixed(2)} {unit}
        </text>
      </svg>
      <span className="text-sm font-medium text-slate-600">{label}</span>
    </div>
  );
}

interface MetricGaugeProps {
  value: number;
  label: string;
  unit: string;
  color?: string;
}

export function MetricGauge({ value, label, unit, color }: MetricGaugeProps) {
  const percentage = Math.min(100, Math.max(0, value));
  
  return (
    <div className="flex flex-col items-center p-4 bg-white rounded-lg shadow-sm border border-slate-200">
      <div className="relative w-32 h-16 overflow-hidden">
        <div className="absolute w-32 h-32 rounded-full border-8 border-slate-100"></div>
        <div 
          className="absolute w-32 h-32 rounded-full border-8 border-transparent"
          style={{
            borderTopColor: color || "#2563eb",
            borderRightColor: percentage > 25 ? (color || "#2563eb") : "transparent",
            borderBottomColor: percentage > 50 ? (color || "#2563eb") : "transparent",
            borderLeftColor: percentage > 75 ? (color || "#2563eb") : "transparent",
            transform: "rotate(-45deg)"
          }}
        ></div>
        <div className="absolute inset-2 bg-white rounded-full flex items-center justify-center">
          <span className="text-lg font-bold text-slate-800">{value.toFixed(1)}{unit}</span>
        </div>
      </div>
      <span className="mt-2 text-sm font-medium text-slate-600">{label}</span>
    </div>
  );
}

interface LinearGaugeProps {
  value: number;
  min: number;
  max: number;
  label: string;
  unit: string;
  color?: string;
}

export function LinearGauge({ value, min, max, label, unit, color = "#2563eb" }: LinearGaugeProps) {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  
  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-slate-600">{label}</span>
        <span className="text-sm font-bold text-slate-800">{value.toFixed(2)}{unit}</span>
      </div>
      <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ 
            width: `${percentage}%`,
            background: `linear-gradient(90deg, #22c55e 0%, #eab308 50%, #ef4444 100%)`
          }}
        ></div>
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-xs text-slate-400">{min}</span>
        <span className="text-xs text-slate-400">{max}</span>
      </div>
    </div>
  );
}

interface RealTimeGaugeProps {
  value: number;
  label: string;
  unit: string;
  min?: number;
  max?: number;
  color?: string;
}

export function RealTimeGauge({ 
  value, 
  label, 
  unit, 
  min = 0, 
  max = 100, 
  color = "#2563eb" 
}: RealTimeGaugeProps) {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
      <div className="flex justify-between items-start mb-2">
        <span className="text-sm font-medium text-slate-600">{label}</span>
        <span 
          className="text-2xl font-bold"
          style={{ color: color }}
        >
          {value.toFixed(2)}
          <span className="text-sm font-normal text-slate-500 ml-1">{unit}</span>
        </span>
      </div>
      
      <div className="relative h-4 bg-slate-100 rounded-full overflow-hidden">
        <div 
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-300 ease-out"
          style={{ 
            width: `${percentage}%`,
            backgroundColor: color
          }}
        ></div>
        
        {[25, 50, 75].map((pos) => (
          <div 
            key={pos}
            className="absolute top-0 bottom-0 w-0.5 bg-slate-300"
            style={{ left: `${pos}%` }}
          ></div>
        ))}
      </div>
      
      <div className="flex justify-between mt-1 text-xs text-slate-400">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
