"use client";

import { useState } from "react";

const plans = [
  {
    name: "Starter",
    price: "$29",
    period: "/month",
    description: "Perfect for small projects and startups",
    features: ["5 Users", "10GB Storage", "Basic Analytics", "Email Support"],
    cta: "Start Free Trial",
    highlighted: false,
  },
  {
    name: "Professional",
    price: "$99",
    period: "/month",
    description: "Best for growing teams and businesses",
    features: [
      "25 Users",
      "100GB Storage",
      "Advanced Analytics",
      "Priority Support",
      "API Access",
      "Custom Integrations",
    ],
    cta: "Get Started",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$299",
    period: "/month",
    description: "For large-scale organizations",
    features: [
      "Unlimited Users",
      "1TB Storage",
      "Real-time Analytics",
      "24/7 Phone Support",
      "Full API Access",
      "SSO & SAML",
      "Dedicated Manager",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export default function PlanSelector() {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");

  return (
    <div className="space-y-4">
      <div className="flex justify-center items-center gap-3">
        <span className={`text-sm ${billingCycle === "monthly" ? "text-gray-900 font-medium" : "text-gray-500"}`}>
          Monthly
        </span>
        <button
          onClick={() => setBillingCycle(billingCycle === "monthly" ? "yearly" : "monthly")}
          className="relative w-14 h-7 bg-gray-200 rounded-full transition-colors"
        >
          <span
            className={`absolute top-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform ${
              billingCycle === "yearly" ? "translate-x-7" : "translate-x-0.5"
            }`}
          />
        </button>
        <span className={`text-sm ${billingCycle === "yearly" ? "text-gray-900 font-medium" : "text-gray-500"}`}>
          Yearly
          <span className="ml-1 text-green-600 text-xs font-semibold">Save 20%</span>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-xl p-6 border-2 transition-all hover:shadow-lg ${
              plan.highlighted
                ? "border-indigo-500 shadow-md bg-white"
                : "border-gray-200 bg-white"
            }`}
          >
            {plan.highlighted && (
              <span className="inline-block bg-indigo-100 text-indigo-700 text-xs font-semibold px-2 py-1 rounded-full mb-3">
                Most Popular
              </span>
            )}
            <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
            <p className="text-gray-500 text-sm mt-1">{plan.description}</p>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
              <span className="text-gray-500">{plan.period}</span>
            </div>
            <ul className="mt-6 space-y-2">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm text-gray-600">
                  <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {feature}
                </li>
              ))}
            </ul>
            <button
              className={`mt-6 w-full py-2.5 rounded-lg font-medium transition-colors ${
                plan.highlighted
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {plan.cta}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
