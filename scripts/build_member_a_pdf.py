"""Build the four-page Member A handoff PDF (requires reportlab)."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results/member_a"
OUTPUT = ROOT / "docs/Member_A_M2_Handoff.pdf"
INK = colors.HexColor("#18354A")
PALE = colors.HexColor("#ECF2F5")
STYLES = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=23,
                            leading=27, textColor=INK, spaceAfter=10),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=10,
                          leading=14, textColor=colors.HexColor("#52616B"), spaceAfter=12),
    "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12,
                              leading=16, textColor=INK, spaceBefore=9, spaceAfter=6),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                           leading=13, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                            leading=10.5, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.4,
                           leading=11),
}


def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def table(rows, widths):
    cells = [[p(escape(str(cell)), "cell") for cell in row] for row in rows]
    obj = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    obj.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), .7, INK),
        ("LINEBELOW", (0, 1), (-1, -1), .25, colors.HexColor("#D6E0E6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return obj


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D6E0E6"))
    canvas.line(44, 39, 568, 39)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52616B"))
    canvas.drawString(44, 26, "DSC 200 | Member A contribution package | November 16, 2026")
    canvas.drawRightString(568, 26, f"{doc.page}")
    canvas.restoreState()


def main():
    summary = json.loads((RESULTS / "summary.json").read_text())
    bedrooms = json.loads((RESULTS / "rent_by_bedroom_plot_group.json").read_text())
    checks = json.loads((RESULTS / "integration_checks.json").read_text())
    assert checks["all_passed"], "Run the verification script before building this handoff."
    story = [
        p("Member A: data &amp; analysis", "title"),
        p("M2 contribution package | UCSD-area rental price analysis", "sub"),
        p("<b>Purpose.</b> Ready-to-integrate data description, processing decisions, initial results and unit-test evidence. This is not the complete group submission. Member B owns requirements, diagrams and filter code; Member C integrates the report and functional tests. Students write their own reflection."),
        p("1. Data Models - report-ready description", "heading"),
        p("The frozen dataset contains <b>2,690 unique rental listing IDs</b> returned by RentCast for a 10-mile straight-line radius around the UCSD reference point (32.8801, -117.2340), with provider status Active. Collection ran on <b>November 16, 2026, 10:21:39-10:23:19 Pacific</b>. One row represents one provider advertisement. Its room-versus-entire-unit or floorplan basis has not been independently verified."),
        p("Core variables are advertised monthly USD, bedrooms, bathrooms, reported floor area, property type and location. Floor area is missing for <b>85 records</b>; all remain in monthly-rent analysis, while <b>2,605</b> support price-per-square-foot analysis."),
        table([
            ["Fields in frozen listings (20 columns)", "Meaning / type"],
            ["id", "Unique provider listing identifier; TEXT primary key"],
            ["formattedAddress, city, state, zipCode", "Location labels; TEXT (postal codes stay text)"],
            ["latitude, longitude", "Coordinates in decimal degrees; REAL"],
            ["propertyType, bedrooms, bathrooms", "Provider category; numeric room counts; 0 bedrooms = studio"],
            ["price, squareFootage", "Monthly USD; reported sqft (nullable)"],
            ["status, listedDate, lastSeenDate, daysOnMarket", "Provider status/date strings; market duration in days"],
            ["sourcePageOffset, sourceRequestedAtUtc", "Page offset and request timestamp for provenance"],
            ["distanceToCampusMiles, advertisedRentPerSqft", "Frozen straight-line miles and USD/sqft/month"],
        ], [248, 276]),
        p("Storage and management", "heading"),
        p("Frozen SQLite tables: <b>listings</b> (2,690 rows, 20 columns), <b>raw_listings</b> (complete JSON linked by ID), and <b>snapshot_metadata</b>. Original API pages, schema and SHA-256 checksums remain alongside the database. The pipeline reads it in read-only mode, verifies integrity, and writes a separate <b>analysis_listings</b> table (43 columns, unique ID index) plus JSON export. Summary tables and figures are separate artifacts."),
        p("Full column-by-column definitions: docs/data_dictionary.md. Derived database: data/processed/member_a/analysis.sqlite. Frozen snapshot: data/frozen/ucsd_rentals_2026-11-16_102139_PT/.", "small"),
        PageBreak(),
        p("Rules, limits &amp; first findings", "title"),
        p("2. Assumptions &amp; Constraints - report-ready text", "heading"),
        p("We treat price as advertised monthly USD and squareFootage as reported square feet. This single provider snapshot describes the query result, not all UCSD-area rentals or changes over time. Active status does not independently confirm current availability. Ads may differ in room-versus-unit basis, fees, concessions, furniture and lease duration. Distance is straight-line distance to a fixed campus point, not travel time. Shared coordinates may identify different units or floorplans. Missing area is not imputed, and unusual observations are retained with review flags. Descriptive comparisons do not establish a causal effect of distance on rent."),
        p("3. Implemented processing decisions", "heading"),
        p("<b>Preserve:</b> all original rows, IDs, columns and source values; do not deduplicate by coordinates. Reject missing/duplicate IDs and failed snapshot checks. Use separate typed columns for analysis."),
        p("<b>Eligibility:</b> finite positive rent, valid coordinates within 10 miles, and Active status; area-based metrics additionally require finite positive area. Unit price = price / area. Invalid denominators return missing. Haversine distance uses radius 3,958.7613 miles."),
        p("<b>Review flags:</b> bedroom-specific 1.5 IQR rent fences (group n &gt;= 4); area below 250 or above 5,000 sqft; room-related address wording; Multi-Family type; and market duration above 365 days. No automatic removal or winsorization. Flags are heuristics, not verified errors."),
        p("<b>Summaries:</b> n, median, mean, quartiles, minimum and maximum; quartiles use linear interpolation. n_valid is the denominator. Bins are [0,1], (1,2], (2,3], (3,5] and (5,10] miles. The plot combines 4-7 bedrooms as 4+ BR; detailed tables retain exact counts."),
        p("4. Initial descriptive evidence", "heading"),
        p(f"All <b>{summary['rent_analysis_n']:,}</b> records qualify for monthly-rent analysis. Median advertised monthly rent is <b>${summary['monthly_rent_median_usd']:,.0f}</b> (range $810-$25,000). Median unit price is <b>${summary['rent_per_sqft_median_usd']:.2f}/sqft/month</b> (n=2,605)."),
        table([["Bedroom group", "n", "Median USD/month", "Middle 50% (Q1-Q3)"]] + [
            [r["bedroom_plot_group"], f"{r['n_valid']:,}", f"${r['median']:,.2f}",
             f"${r['q1']:,.2f} - ${r['q3']:,.2f}"] for r in bedrooms
        ], [130, 60, 154, 180]),
        Spacer(1, 8),
        p("Review counts: 2 room-wording ads; 12 extreme-area records; 346 records over 365 days on market; 219 bedroom-IQR rent flags. Categories can overlap. There are 1,326 coordinate pairs, including 1,573 listings sharing coordinates; the largest group has 63 ads. All remain in the baseline."),
        p("Sensitivity: the median of per-coordinate median rents is $3,326.50, compared with the listing-level $3,295. Coordinates are only a coarse clustering proxy, not verified buildings. Sources: generated summary.json and bedroom-group table.", "small"),
        PageBreak(),
        p("Initial analysis figures", "title"),
        p("Descriptive results for the frozen RentCast query; retain all eligible advertisements.", "sub"),
        Image(str(RESULTS / "rent_by_bedrooms.png"), width=450, height=283.5),
        Spacer(1, 5),
        Image(str(RESULTS / "rent_by_distance.png"), width=450, height=283.5),
        p("Interpretation: more bedrooms generally have higher advertised prices in this snapshot. Distance patterns vary by bedroom group. Even within 1BR/2BR, property mix and listing basis can differ; 0-1 mile samples are small. IQR bars are distributions, not confidence intervals or causal estimates.", "small"),
        PageBreak(),
        p("Tests, progress &amp; handoff", "title"),
        p("5. Selected unit cases - all three passed", "heading"),
        p("<b>Shared preconditions:</b> install analysis dependencies, import ucsd_rentals.data, and use synthetic fixtures independent of the frozen data. No API or database access is required for these unit cases."),
        p("<b>UT-A1 - ordinary unit price.</b> Input/step: call unit_rent(3000, 1000). Expected/postcondition: return 3.0 USD/sqft/month within floating-point tolerance, without exception. <b>Actual: PASS.</b>"),
        p("<b>UT-A2 - unusable area.</b> Input/steps: call unit_rent(3000, area) for None, 0, -100, NaN, +infinity and -infinity. Expected/postcondition: None for every case; no division error or nonfinite result. <b>Actual: PASS, all six subcases.</b>"),
        p("<b>UT-A3 - grouping and missing values.</b> Inputs: Studio [1000, 3000, None]; 1BR [1800, 2200, 8000, None]. Step: group_summary by bedroom label. Expected/postcondition: exactly two groups; Studio n_records/n_valid/n_missing = 3/2/1 and median = 2000; 1BR = 4/3/1 and median = 2200. Missing values do not count as zero. <b>Actual: PASS.</b>"),
        p(f"Additional verification: <b>{len(checks['checks'])} data/integration checks passed</b>, including exact preservation of 20 source columns, row counts, missing-area behavior, medians independently recomputed with Python statistics, export consistency and 15 frozen file checksums. These do not replace the group's three functional test cases."),
        p("6. Rubric mapping and remaining responsibilities", "heading"),
        table([
            ["Module", "A provides / current state"],
            ["Data Models; Assumptions & Constraints", "Implemented data model, full dictionary, storage design and explicit processing/interpretation rules."],
            ["Unit Test Cases", "Three defined, executable cases with expected and actual results; all passing."],
            ["Code Submission; Progress Check", "Offline preparation and descriptive analysis run successfully. B assigns final requirement IDs; C maps evidence and remaining work to the spec."],
            ["B: requirements and architecture", "Write requirements and three UML types with descriptions/justifications; implement agreed filters using the derived table."],
            ["C: functional tests and final PDF", "Document/run three functional cases; integrate selected A materials with B's sections and the team's own reflection."],
        ], [174, 350]),
        p("Run and review", "heading"),
        p("Install requirements-analysis.txt; run <b>python scripts/run_member_a.py</b>, then <b>PYTHONPATH=src python -m unittest tests.test_member_a -v</b> and <b>python scripts/verify_member_a.py</b>. No API key is needed. Read docs/member_a_handoff.md for interfaces and results/member_a/ for evidence.", "small"),
        p("<b>Before submission:</b> team members review and understand the code and results. The instructor's rubric says reflection should not be AI-generated; no reflection is supplied. AI assistance is disclosed in README. Submit one PDF plus code ZIP or an accessible GitHub link. Spec maximum: four pages unless justified; do not submit this contribution package as the complete spec.", "small"),
    ]
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=(612, 792), leftMargin=44,
                            rightMargin=44, topMargin=40, bottomMargin=50,
                            title="DSC200 M2 - Member A Data and Analysis Handoff",
                            author="DSC200 project team", allowSplitting=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
