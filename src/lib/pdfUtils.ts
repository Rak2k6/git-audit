import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";

// Use the bundled worker from pdfjs-dist (Vite will resolve this correctly)
GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

/**
 * Extracts all text content from a PDF file.
 * Uses Mozilla's pdf.js for accurate, layout-aware text extraction.
 */
export async function extractTextFromPdf(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await getDocument({ data: new Uint8Array(arrayBuffer) }).promise;

  const pageTexts: string[] = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();

    // Build text preserving line structure using vertical position (y-coordinate)
    const items = content.items.filter(
      (item): item is TextItem => "str" in item && item.str.length > 0
    );

    if (items.length === 0) continue;

    // Group items by their vertical position to reconstruct lines
    const lines: { y: number; segments: { x: number; text: string }[] }[] = [];
    const Y_TOLERANCE = 2; // pixels tolerance for same-line grouping

    for (const item of items) {
      const y = item.transform[5]; // vertical position
      const x = item.transform[4]; // horizontal position

      let existingLine = lines.find((l) => Math.abs(l.y - y) < Y_TOLERANCE);
      if (existingLine) {
        existingLine.segments.push({ x, text: item.str });
      } else {
        lines.push({ y, segments: [{ x, text: item.str }] });
      }
    }

    // Sort lines top-to-bottom (higher y = higher on page in PDF coordinate space)
    lines.sort((a, b) => b.y - a.y);

    // Sort segments left-to-right within each line, join with appropriate spacing
    const lineTexts = lines.map((line) => {
      line.segments.sort((a, b) => a.x - b.x);
      return line.segments.map((s) => s.text).join(" ");
    });

    pageTexts.push(lineTexts.join("\n"));
  }

  return pageTexts.join("\n\n");
}
