"""Create a real image-only PDF fixture without any model or network access."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def font(size, bold=False):
    candidates = ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def main():
    output = ROOT / "fixtures/reports"
    output.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1275, 1650), "#fbfbf8")
    draw = ImageDraw.Draw(image)
    draw.text((100, 85), "SYNTHETIC INSPECTION REPORT", font=font(36, True), fill="#222222")
    draw.text((100, 145), "Demonstration only   |   Not for operating decisions", font=font(22), fill="#a34b35")
    draw.line((100, 210, 1175, 210), fill="#b8bdc1", width=2)
    for y, line in zip((255, 300, 345), ("Report ID: SYN-INS-001", "Inspection date: 17 October 2026", "Units: thickness in mm; pressure in bar")):
        draw.text((100, y), line, font=font(25), fill="#4d565d")
    headers = ["Asset tag", "Thickness", "Pressure"]
    positions = [125, 530, 870]
    draw.rectangle((100, 435, 1175, 505), fill="#e5ebef")
    for x, title in zip(positions, headers):
        draw.text((x, 453), title, font=font(25, True), fill="#293744")
    records = [("P-101", "5.8 mm", "12 bar"), ("P-101", "5.6 mm", "12 bar"), ("P-202", "7.2 mm", "8 bar")]
    for i, row in enumerate(records):
        top = 505 + i*95
        draw.rectangle((100, top, 1175, top+95), outline="#c8cfd4", width=1)
        for x, value in zip(positions, row):
            draw.text((x, top+30), value, font=font(28), fill="#333b40")
    draw.text((100, 885), "Inspector observations", font=font(27, True), fill="#25313c")
    for y, text in zip((945, 990, 1035, 1080), (
        "Three ultrasonic thickness readings are recorded above.",
        "No historical readings or corrosion rates are supplied.",
        "No approved minimum thickness or decision rule is supplied.",
        "Engineering review is required; no approval is issued.")):
        draw.text((100, y), text, font=font(23), fill="#4d565d")
    draw.text((100, 1465), "SYNTHETIC DATA     |     Source page 1 of 1", font=font(21), fill="#91999e")
    image.save(output / "synthetic-inspection-scan.png")
    image.save(output / "synthetic-inspection-scan.pdf", "PDF", resolution=150)
    (output / "synthetic-thickness.csv").write_text("tag,thickness_mm,pressure_bar,page\nP-101,5.8,12,1\nP-101,5.6,12,1\nP-202,7.2,8,1\n", encoding="utf-8")
    print("Created synthetic image-only PDF, image and thickness CSV")


if __name__ == "__main__":
    main()

