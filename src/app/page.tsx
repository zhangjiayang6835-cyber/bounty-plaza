import { Suspense } from "react";
import Dashboard from "@/components/Dashboard";
import Navbar from "@/components/Navbar";
import Loading from "@/components/Loading";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <Suspense fallback={<Loading />}>
          <Dashboard />
        </Suspense>
      </div>
    </main>
  );
}
