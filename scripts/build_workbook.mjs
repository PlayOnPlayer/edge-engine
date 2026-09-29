import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "reports";
const fontFamily = "Arial";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

async function loadCsv(path) {
  try {
    return parseCsv(await fs.readFile(path, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function asTyped(value, index, numericColumns) {
  if (value === "") return null;
  if (numericColumns.has(index)) {
    const number = Number(value);
    return Number.isFinite(number) ? number : value;
  }
  return value;
}

function styleTitle(sheet, range, subtitle) {
  sheet.getRange(range).format.font = { name: fontFamily, size: 16, bold: true, color: "#172033" };
  const lastColumn = range.split(":")[1].replace(/[0-9]/g, "");
  sheet.getRange(`A2:${lastColumn}2`).format.borders = { bottom: { style: "thin", color: "#AAB4C4" } };
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange(`A3:${lastColumn}3`).format.font = { name: fontFamily, size: 10, italic: true, color: "#5D6675" };
}

function styleHeader(range) {
  range.format = {
    fill: "#23324D",
    font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { insideVertical: { style: "thin", color: "#FFFFFF" } },
  };
  range.format.rowHeight = 30;
}

const tradeRows = await loadCsv("reports/paper_trades.csv");
const comparisonRows = await loadCsv("reports/strategy_comparison.csv");
const dailyRows = await loadCsv("reports/daily_summary.csv");

const workbook = Workbook.create();
const dashboard = workbook.worksheets.add("Dashboard");
const comparison = workbook.worksheets.add("Strategy Comparison");
const trades = workbook.worksheets.add("Paper Trades");
const daily = workbook.worksheets.add("Daily Summary");
const notes = workbook.worksheets.add("Method and Sources");

for (const sheet of [dashboard, comparison, trades, daily, notes]) {
  sheet.showGridLines = false;
  sheet.getRange("A1:AZ5000").format.font = { name: fontFamily, size: 10, color: "#202632" };
}

dashboard.getRange("A2:H2").merge();
dashboard.getRange("A2").values = [["Edge Engine paper trading"]];
styleTitle(dashboard, "A2:H2", "Read-only research results. Demo and REST-poll observations are labeled separately.");
dashboard.getRange("A6:B11").values = [
  ["Metric", "Value"],
  ["Simulated trades", null],
  ["Net paper P&L", null],
  ["Pair completion", null],
  ["Estimated fees", null],
  ["Maker rebates", null],
];
styleHeader(dashboard.getRange("A6:B6"));
dashboard.getRange("B7").formulas = [["=SUM('Strategy Comparison'!B7:B106)"]];
dashboard.getRange("B8").formulas = [["=SUM('Strategy Comparison'!I7:I106)"]];
dashboard.getRange("B9").formulas = [["=IF(B7=0,0,SUM('Strategy Comparison'!C7:C106)/B7)"]];
dashboard.getRange("B10").formulas = [["=SUM('Strategy Comparison'!G7:G106)"]];
dashboard.getRange("B11").formulas = [["=SUM('Strategy Comparison'!H7:H106)"]];
dashboard.getRange("B7").format.numberFormat = "#,##0";
dashboard.getRange("B8:B8").format.numberFormat = "$#,##0.00;[Red]-$#,##0.00";
dashboard.getRange("B9").format.numberFormat = "0.0%";
dashboard.getRange("B10:B11").format.numberFormat = "$#,##0.00;[Red]-$#,##0.00";
dashboard.getRange("A7:A11").format.font = { name: fontFamily, bold: true, color: "#38445A" };
dashboard.getRange("A7:B11").format.borders = { bottom: { style: "thin", color: "#E2E6EC" } };

dashboard.getRange("A14:H18").values = [
  ["How to read this version", null, null, null, null, null, null, null],
  ["Data mode", "DEMO rows prove the pipeline. REST_POLL rows come from live public endpoints.", null, null, null, null, null, null],
  ["Fill model", "REALISTIC_TRADE_THROUGH requires the observed last trade to move through a resting quote.", null, null, null, null, null, null],
  ["Current limit", "BBO polling cannot measure queue position, partial fills, or depth-sensitive exit differences.", null, null, null, null, null, null],
  ["Launch status", "The free forward probe observed one production BTC 15-minute market on September 29, 2026; availability remains subject to staged rollout.", null, null, null, null, null, null],
];
dashboard.getRange("A14:H14").merge();
dashboard.getRange("A14").format = { fill: "#E8EDF5", font: { name: fontFamily, bold: true, color: "#23324D" } };
for (let row = 15; row <= 18; row += 1) {
  dashboard.getRange(`B${row}:H${row}`).merge();
  dashboard.getRange(`A${row}`).format.font = { name: fontFamily, bold: true, color: "#38445A" };
  dashboard.getRange(`B${row}:H${row}`).format.wrapText = true;
}
dashboard.getRange("A1:H20").format.autofitColumns();
dashboard.getRange("A:A").format.columnWidth = 22;
dashboard.getRange("B:H").format.columnWidth = 17;
dashboard.getRange("B15:H18").format.columnWidth = 14;
dashboard.getRange("A15:H18").format.rowHeight = 34;

comparison.getRange("A2:L2").merge();
comparison.getRange("A2").values = [["Strategy comparison"]];
styleTitle(comparison, "A2:L2", "Results use the same observations and fee assumptions for each strategy.");
if (comparisonRows.length) {
  const numeric = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
  const matrix = comparisonRows.map((row, rowIndex) => row.map((value, index) => rowIndex === 0 ? value : asTyped(value, index, numeric)));
  comparison.getRange("A6").write(matrix);
  styleHeader(comparison.getRange(`A6:L6`));
  comparison.tables.add(`A6:L${5 + matrix.length}`, true, "StrategyComparisonTable").style = "TableStyleMedium2";
  comparison.getRange(`D7:D${5 + matrix.length}`).format.numberFormat = "0.0%";
  comparison.getRange(`F7:L${5 + matrix.length}`).format.numberFormat = "$#,##0.00;[Red]-$#,##0.00";
  const chart = comparison.charts.add("bar", [comparison.getRange(`A6:A${5 + matrix.length}`), comparison.getRange(`I6:I${5 + matrix.length}`)]);
  chart.title = "Net paper P&L by strategy";
  chart.titleTextStyle.typeface = fontFamily;
  chart.legend = { position: "bottom", textStyle: { typeface: fontFamily } };
  chart.yAxis = { numberFormatCode: "$#,##0.00", numberFormatSourceLinked: false, textStyle: { typeface: fontFamily } };
  chart.setPosition("N6", "U20");
}
comparison.getRange("A1:L30").format.autofitColumns();
comparison.getRange("A:A").format.columnWidth = 22;
comparison.freezePanes.freezeRows(6);

trades.getRange("A2:AD2").merge();
trades.getRange("A2").values = [["Paper trades"]];
styleTitle(trades, "A2:AD2", "One row per completed simulation. Assumptions and data mode remain visible for audit.");
if (tradeRows.length) {
  const numeric = new Set([11, 12, 13, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27, 28]);
  const matrix = tradeRows.map((row, rowIndex) => row.map((value, index) => rowIndex === 0 ? value : asTyped(value, index, numeric)));
  trades.getRange("A6").write(matrix);
  styleHeader(trades.getRange("A6:AD6"));
  trades.tables.add(`A6:AD${5 + matrix.length}`, true, "PaperTradesTable").style = "TableStyleMedium2";
  trades.getRange(`L7:R${5 + matrix.length}`).format.numberFormat = "0.000";
  trades.getRange(`U7:V${5 + matrix.length}`).format.numberFormat = "$#,##0.00";
  trades.getRange(`W7:W${5 + matrix.length}`).format.numberFormat = "0.000";
  trades.getRange(`Y7:AC${5 + matrix.length}`).format.numberFormat = "$#,##0.00;[Red]-$#,##0.00";
  trades.getRange(`AC7:AC${5 + matrix.length}`).conditionalFormats.add("cellIs", {
    operator: "lessThan", formula: 0, format: { font: { color: "#B42318" }, fill: "#FDECEC" },
  });
}
trades.getRange("A1:AD20").format.autofitColumns();
trades.getRange("A:A").format.columnWidth = 34;
trades.getRange("F:F").format.columnWidth = 26;
trades.getRange("J:J").format.columnWidth = 24;
trades.getRange("T:T").format.columnWidth = 28;
trades.getRange("AD:AD").format.columnWidth = 70;
trades.getRange("AD:AD").format.wrapText = true;
trades.freezePanes.freezeRows(6);
trades.freezePanes.freezeColumns(5);

daily.getRange("A2:H2").merge();
daily.getRange("A2").values = [["Daily summary"]];
styleTitle(daily, "A2:H2", "Daily totals by strategy and data mode present in the paper ledger.");
if (dailyRows.length) {
  const numeric = new Set([2, 3, 4, 5, 6, 7]);
  const matrix = dailyRows.map((row, rowIndex) => row.map((value, index) => rowIndex === 0 ? value : asTyped(value, index, numeric)));
  daily.getRange("A6").write(matrix);
  styleHeader(daily.getRange("A6:H6"));
  daily.tables.add(`A6:H${5 + matrix.length}`, true, "DailySummaryTable").style = "TableStyleMedium2";
  daily.getRange(`D7:F${5 + matrix.length}`).format.numberFormat = "$#,##0.00;[Red]-$#,##0.00";
}
daily.getRange("A1:H30").format.autofitColumns();
daily.freezePanes.freezeRows(6);

notes.getRange("A2:F2").merge();
notes.getRange("A2").values = [["Method and sources"]];
styleTitle(notes, "A2:F2", "Current assumptions and authoritative documentation used by V1.");
notes.getRange("A6:C16").values = [
  ["Item", "Current treatment", "Source"],
  ["Trading access", "No trading code, wallet, or order credentials", "Repository design"],
  ["Polymarket market data", "Public REST polling; WebSocket deferred because it requires API-key authentication", "https://docs.polymarket.us/api-reference/websocket/markets"],
  ["Market family", "BTC 15-minute Up/Down discovered from assetPriceTerms", "https://docs.polymarket.us/faqs/crypto-faqs"],
  ["Settlement", "BRTI 60-sample opening and closing averages; not yet modeled in V1", "https://docs.polymarket.us/faqs/crypto-faqs"],
  ["Taker fee", "0.0695 × contracts × price × (1-price), banker-rounded to cents", "https://docs.polymarket.us/fees"],
  ["Maker rebate", "0.0125 × contracts × price × (1-price), banker-rounded to cents", "https://docs.polymarket.us/fees"],
  ["External BTC", "Latest Coinbase BTC-USD public trade", "https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-trades"],
  ["Fill assumption", "Strict observed trade-through; full quantity; no partial fills", "Research assumption E001"],
  ["US market structure", "YES and NO are complementary directions of one instrument; BBO-only smart exits are economically equivalent before depth effects", "https://docs.polymarket.us/concepts/orders"],
  ["Production status", "The changelog describes a staged rollout; this project observed one matching production market during the free probe and keeps discovery as a hard gate", "https://docs.polymarket.us/changelog"],
];
styleHeader(notes.getRange("A6:C6"));
notes.getRange("A7:C16").format.wrapText = true;
notes.getRange("A:A").format.columnWidth = 23;
notes.getRange("B:B").format.columnWidth = 65;
notes.getRange("C:C").format.columnWidth = 72;
notes.getRange("A7:C16").format.rowHeight = 38;
notes.freezePanes.freezeRows(6);

const dashboardInspect = await workbook.inspect({
  kind: "table", range: "Dashboard!A1:H20", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 12,
});
console.log(dashboardInspect.ndjson);
const errors = await workbook.inspect({
  kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
for (const sheetName of ["Dashboard", "Strategy Comparison", "Paper Trades", "Daily Summary", "Method and Sources"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/preview_${sheetName.toLowerCase().replaceAll(" ", "_")}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/edge_engine_review.xlsx`);
console.log(`Created ${outputDir}/edge_engine_review.xlsx`);
