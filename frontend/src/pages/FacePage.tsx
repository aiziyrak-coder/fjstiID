import { useRef, useState } from "react";
import { api } from "../api";

export function FacePage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [result, setResult] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const start = async () => {
    const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
    setStream(s);
    if (videoRef.current) {
      videoRef.current.srcObject = s;
      await videoRef.current.play();
    }
  };

  const stop = () => {
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
  };

  const showResult = (res: { matched: boolean; confidence?: number; user?: any }) => {
    if (res.matched && res.user) {
      setResult(`Mos keldi: ${res.user.full_name} (${Math.round((res.confidence || 0) * 100)}%)`);
    } else {
      setResult("Mos kelmadi — bazadagi rasm bilan solishtirildi");
    }
  };

  const captureAndVerify = async () => {
    if (!videoRef.current) return;
    setBusy(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.videoWidth || 640;
      canvas.height = videoRef.current.videoHeight || 480;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(videoRef.current, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
      if (!blob) throw new Error("Rasm olinmadi");
      const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
      showResult(await api.verifyFace(file));
    } catch (e) {
      setResult(e instanceof Error ? e.message : "Xato");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2>FaceID tekshiruv</h2>
      <p className="muted">
        Kameraga qarang yoki fayl yuklang. Tizim foydalanuvchi qo‘shilganda yuklangan rasm bilan solishtiradi.
      </p>
      <div className="panel">
        <video
          ref={videoRef}
          style={{ width: "100%", maxWidth: 480, borderRadius: 12, background: "#111", display: "block" }}
          muted
          playsInline
        />
        <div className="row" style={{ marginTop: "1rem" }}>
          {!stream ? (
            <button className="btn accent" onClick={start}>
              Kamerani yoqish
            </button>
          ) : (
            <>
              <button className="btn" disabled={busy} onClick={captureAndVerify}>
                {busy ? "Tekshirilmoqda..." : "Yuzni tekshirish"}
              </button>
              <button className="btn secondary" onClick={stop}>
                To'xtatish
              </button>
            </>
          )}
          <label className="btn secondary" style={{ cursor: "pointer" }}>
            Fayldan solishtirish
            <input
              type="file"
              accept="image/*"
              hidden
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setBusy(true);
                try {
                  showResult(await api.verifyFace(f));
                } catch (err) {
                  setResult(err instanceof Error ? err.message : "Xato");
                } finally {
                  setBusy(false);
                }
              }}
            />
          </label>
        </div>
        {result && <p style={{ marginTop: "1rem", fontWeight: 600 }}>{result}</p>}
      </div>
    </div>
  );
}
