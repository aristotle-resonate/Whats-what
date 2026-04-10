"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { verifyMagicToken, setToken } from "@/lib/api";

type Stage = "verifying" | "success" | "error";

function VerifyInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("verifying");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setErrorMsg("No token found in the link.");
      setStage("error");
      return;
    }

    verifyMagicToken(token)
      .then((data) => {
        setToken(data.access_token);
        setStage("success");
        setTimeout(() => {
          router.replace(data.onboarding_completed ? "/" : "/onboarding");
        }, 1000);
      })
      .catch(() => {
        setErrorMsg(
          "This link is invalid or has expired. Please request a new one."
        );
        setStage("error");
      });
  }, [params, router]);

  return (
    <div className="text-center space-y-4">
      {stage === "verifying" && (
        <>
          <div className="inline-block h-8 w-8 rounded-full border-2 border-zinc-700 border-t-white animate-spin" />
          <p className="text-sm text-zinc-400">Signing you in…</p>
        </>
      )}
      {stage === "success" && (
        <>
          <div className="text-3xl">✓</div>
          <p className="text-sm text-zinc-300">Signed in! Redirecting…</p>
        </>
      )}
      {stage === "error" && (
        <>
          <div className="text-3xl">✕</div>
          <p className="text-sm text-zinc-400">{errorMsg}</p>
          <a
            href="/auth/sign-in"
            className="inline-block mt-2 text-sm text-white underline"
          >
            Request a new link
          </a>
        </>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Suspense
          fallback={
            <div className="text-center">
              <div className="inline-block h-8 w-8 rounded-full border-2 border-zinc-700 border-t-white animate-spin" />
            </div>
          }
        >
          <VerifyInner />
        </Suspense>
      </div>
    </main>
  );
}
