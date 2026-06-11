#!/usr/bin/env python3
"""Записывает полный JSX из Figma MCP в _context/*.txt (обновить вручную при смене макета)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "web" / "assets" / "figma" / "_context"

# Полный JSX получен через Figma Desktop MCP get_design_context
FILES = {
    "start": r'''const img2 = "http://localhost:3845/assets/488b182ee2274bda0e42f0406d131ba5de756d0c.png";
const img3 = "http://localhost:3845/assets/199c5ba01a61e6cc478ed13de37575b68e5c4776.png";
const img1 = "http://localhost:3845/assets/1563697d12155680b73c4d623f05f35318b669a6.png";
const img4 = "http://localhost:3845/assets/ba682dc3889044076820b4f23216dee0a7394771.png";
const imgBgDecor = "http://localhost:3845/assets/eeb09f2d809e30f9e9d5007b9ceecd44d294b462.svg";
const img = "http://localhost:3845/assets/74d233acd9ce731dee934ef8f8f2bc708144831b.svg";
const imgEllipse28870 = "http://localhost:3845/assets/a40e0eedcff9764cd702a875f13d87d08e61f2a9.svg";
const imgEllipse28871 = "http://localhost:3845/assets/9f73fc3a561e0d7cd8e8ac1508128ea9a7c3f9fb.svg";
const imgEllipse28872 = "http://localhost:3845/assets/e91cb2d5c1e875eac227ebd44377c931e4499406.svg";
const imgVector234257108 = "http://localhost:3845/assets/f6ea418e105ffb53210064f86e2c3f7a672f8b0e.svg";
const imgStar19 = "http://localhost:3845/assets/ec4ff578e09eb81b02098e81b97a174d5fbb8b1b.svg";
const img5 = "http://localhost:3845/assets/dd849ce3e75e01bc98af7d108143446b11e5b96c.svg";

export default function Start() {
  return (
    <div className="bg-gradient-to-b from-[#ecfffe] relative size-full to-[#9effa8]" data-node-id="25:1367" data-name="Start">
      <div className="absolute h-[882.209px] left-[-48px] top-[-134px] w-[726.743px]" data-node-id="25:1368" data-name="BG Decor">
        <img alt="" className="absolute block inset-0 max-w-none size-full" src={imgBgDecor} />
      </div>
      <div className="absolute h-[501.95px] left-[-284px] top-[244.34px] w-[899.382px]" data-node-id="25:1372" data-name="Трава2">
        <div aria-hidden className="absolute inset-0 pointer-events-none">
          <img alt="" className="absolute max-w-none object-cover size-full" src={img2} />
          <img alt="" className="absolute max-w-none object-cover size-full" src={img3} />
        </div>
      </div>
      <div className="absolute h-[329px] left-[-25px] top-[466px] w-[428px]" data-node-id="25:1373" data-name="Дымка">
        <div className="absolute inset-[-47.39%_-36.43%]">
          <img alt="" className="block max-w-none size-full" src={img} />
        </div>
      </div>
      <div className="absolute flex h-[935.103px] items-center justify-center left-[57px] top-[204px] w-[791.325px]">
        <div className="-scale-y-100 flex-none rotate-[157.6deg]">
          <div className="h-[793.404px] relative w-[528.936px]" data-node-id="25:1374" data-name="Трава1">
            <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={img1} />
          </div>
        </div>
      </div>
      <div className="absolute contents left-[356px] top-[504px]" data-node-id="25:1375" data-name="Тень">
        <div className="absolute h-[105.734px] left-[356px] mix-blend-multiply top-[504px] w-[201.237px]" data-node-id="25:1376">
          <div className="absolute inset-[-24.52%_-12.88%]">
            <img alt="" className="block max-w-none size-full" src={imgEllipse28870} />
          </div>
        </div>
        <div className="absolute h-[64.805px] left-[356px] mix-blend-multiply top-[521.05px] w-[201.237px]" data-node-id="25:1377">
          <div className="absolute inset-[-40%_-12.88%]">
            <img alt="" className="block max-w-none size-full" src={imgEllipse28871} />
          </div>
        </div>
        <div className="absolute h-[46.046px] left-[356px] mix-blend-multiply top-[530.43px] w-[201.237px]" data-node-id="25:1378">
          <div className="absolute inset-[-56.3%_-12.88%]">
            <img alt="" className="block max-w-none size-full" src={imgEllipse28872} />
          </div>
        </div>
      </div>
      <div className="absolute flex items-center justify-center left-[224.48px] size-[386.283px] top-[228.02px]">
        <div className="-scale-y-100 flex-none rotate-[-172.92deg]">
          <div className="relative size-[346.249px]" data-node-id="25:1379" data-name="Копилка">
            <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={img4} />
          </div>
        </div>
      </div>
      <div className="-translate-x-1/2 absolute h-[25.149px] left-[calc(50%-0.14px)] top-[61.34px] w-[258.29px]" data-node-id="25:1384" data-name="Лого">
        <img alt="" className="absolute block inset-0 max-w-none size-full" src={img5} />
      </div>
      <p className="-translate-x-1/2 absolute left-[calc(50%+0.23px)] text-[#ff64a2] text-[35.513px] top-[111px] tracking-[-2.4859px] w-[392.458px]" data-node-id="25:1401">{`ИнвестКопилка `}</p>
      <p className="-translate-x-1/2 absolute left-[calc(50%-0.63px)] text-[#122654] text-[17.978px] top-[138.27px] tracking-[-1.2585px] w-[198.678px]" data-node-id="25:1402">против</p>
      <p className="-translate-x-1/2 absolute left-[calc(50%+0.23px)] text-[#122654] text-[35.513px] top-[150.49px] tracking-[-2.4859px] w-[392.458px]" data-node-id="25:1403">монстров-расходов</p>
      <p className="-translate-x-1/2 absolute font-['SB_Sans_Display_BETA2:Extended_Semibold'] left-[calc(50%-0.81px)] text-[37.116px] text-center text-white top-[581.56px] tracking-[-2.5981px] whitespace-nowrap" data-node-id="25:1406">играть</p>
      <div className="absolute flex h-[112.373px] items-center justify-center left-[474.2px] top-[217.89px] w-[119.798px]">
        <div className="flex-none rotate-[82.89deg]">
          <div className="h-[108.282px] relative w-[99.733px]" data-node-id="25:1381">
            <div className="absolute inset-[-3.08%_-4.01%_0_-4.01%]">
              <img alt="" className="block max-w-none size-full" src={imgVector234257108} />
            </div>
          </div>
        </div>
      </div>
      <div className="absolute flex items-center justify-center left-[105px] size-[122.422px] top-[393px]">
        <div className="flex-none rotate-[-23.14deg]">
          <div className="relative size-[93.271px]" data-node-id="25:1382">
            <div className="absolute inset-[10.09%]">
              <img alt="" className="block max-w-none size-full" src={imgStar19} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}''',
}

# Остальные экраны уже частично в _context; start — полный. Онбординги/error/result — через parse из существующих + MCP.
def main():
    CTX.mkdir(parents=True, exist_ok=True)
    for name, body in FILES.items():
        (CTX / f"{name}.txt").write_text(body, encoding="utf-8")
        print("saved", name)


if __name__ == "__main__":
    main()
