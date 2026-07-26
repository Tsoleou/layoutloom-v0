import { useEffect, useRef, useState } from "react";

// The banner is authored at the contract's canvas size; scale it down to fit
// the panel via an iframe rendered by the real browser (so stub mode — whose
// PNG is a blank placeholder — still shows a true banner with text + images).
const W = 1200;
const H = 628;

export function BannerPreview({ src }: { src: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(300);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const scale = width / W;
  return (
    <div className="preview" ref={ref} style={{ height: H * scale }}>
      <iframe
        title="banner"
        src={src}
        scrolling="no"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: W,
          height: H,
          border: 0,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
        }}
      />
    </div>
  );
}
