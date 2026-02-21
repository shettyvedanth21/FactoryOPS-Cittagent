"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function DeviceRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const deviceId = (params.deviceId as string) || "";

  useEffect(() => {
    if (deviceId) {
      router.replace(`/machines/${deviceId}`);
    }
  }, [deviceId, router]);

  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-slate-600">Redirecting...</p>
      </div>
    </div>
  );
}
