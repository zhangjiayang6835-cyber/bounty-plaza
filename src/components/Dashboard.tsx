import { Suspense } from "react";
import PlanSelector from "@/components/PlanSelector";
import StatsCard from "@/components/StatsCard";
import FeatureCard from "@/components/FeatureCard";
import Loading from "@/components/Loading";

const features = [
  {
    title: "Multi-Tenant Architecture",
    description: "Isolated workspaces with per-tenant data segregation",
    icon: "🏢",
  },
  {
    title: "Usage-Based Billing",
    description: "Pay only for what you use with granular metering",
    icon: "💳",
  },
  {
    title: "API Access",
    description: "Full REST API with rate limiting per plan tier",
    icon: "🔌",
  },
  {
    title: "Analytics Dashboard",
    description: "Real-time insights and usage monitoring",
    icon: "📊",
  },
  {
    title: "SSO Integration",
    description: "Enterprise single sign-on support",
    icon: "🔐",
  },
  {
    title: "24/7 Support",
    description: "Priority support with guaranteed response times",
    icon: "🎧",
  },
];

const stats = [
  { label: "Active Subscribers", value: "12,847", change: "+18%" },
  { label: "Monthly Revenue", value: "$284K", change: "+24%" },
  { label: "API Requests/day", value: "1.2M", change: "+31%" },
  { label: "Uptime", value: "99.99%", change: "+0.01%" },
];

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          OmniBlocks SaaS Platform
        </h1>
        <p className="text-gray-600 text-lg">
          Scalable infrastructure for modern applications
        </p>
      </div>

      <PlanSelector />

      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Platform Stats</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <StatsCard key={stat.label} {...stat} />
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </div>
  );
}
