import os
import csv
import logging
from config import COMB_KEYWORDS, COMB_IDX_FORM, EXPECTED_COLUMNS

logger = logging.getLogger(__name__)

class TableProcessor:
    """
    Transform raw OCR tables into a clean, final format.

    Steps:
      1. Merge instructor rows.
      2. Split combined fields.
      3. Fill rows labeled "BRAK" with placeholder columns.
      4. Annotate rows with metadata (kierunek, stopień, semestr).
      5. Construct header and filter valid data rows.
      6. Save result to CSV.
    """

    def __init__(self):
        """
        Initialize TableProcessor by loading configuration parameters.
        """
        self.combined_keywords = COMB_KEYWORDS
        self.combined_idx_form = COMB_IDX_FORM
        self.expected_columns = EXPECTED_COLUMNS

    def merge_instructors_simple(self, table):
        """
        Merge rows of instructor names into corresponding course rows when they appear
        in the pattern: [3-cell row], [>=5-cell row], [3-cell row].

        Args:
            table (list[list[str]]): OCR-extracted table, a list of rows.

        Returns:
            list[list[str]]: New table with instructor rows merged.
        """
        merged = []
        i = 0
        while i < len(table):
            row = table[i]
            # If a 3-cell row is followed by a >=5-cell row and another 3-cell row,
            # combine instructors into the middle row
            if len(row) == 3 and i + 2 < len(table):
                next_row = table[i + 1]
                next_next = table[i + 2]
                if len(next_row) >= 5 and len(next_next) == 3:
                    instr1 = row
                    course = next_row
                    instr2 = next_next

                    merged1 = course[:2] + instr1 + course[2:]
                    merged2 = course[:2] + instr2 + course[2:]

                    merged.append(merged1)
                    merged.append(merged2)
                    i += 3
                    continue

            merged.append(row)
            i += 1

        logger.debug("Merged instructors: %d rows before, %d rows after", len(table), len(merged))
        return merged

    def split_if_combined_fields(self, table):
        """
        Split combined form/education-type fields in a single cell into two separate cells.

        Looks for any keyword in self.combined_keywords inside the cell at index self.combined_idx_form,
        then splits that cell into two parts on the first occurrence of the keyword.

        Args:
            table (list[list[str]]): Table rows to process.

        Returns:
            list[list[str]]: Table with combined fields split.
        """
        new_table = []
        for row in table:
            # Skip rows without the combined-field column
            if self.combined_idx_form >= len(row):
                new_table.append(row)
                continue

            cell = row[self.combined_idx_form]
            found = None
            for kw in self.combined_keywords:
                if kw in cell.lower():
                    found = kw
                    break

            if not found:
                new_table.append(row)
            else:
                parts = row[self.combined_idx_form].split(found, 1)
                left = parts[0].strip()
                right = (found + parts[1]).strip()
                new_row = row[:self.combined_idx_form] + [left, right] + row[self.combined_idx_form+1:]
                new_table.append(new_row)

        logger.debug("Split combined fields: %d rows processed", len(new_table))
        return new_table

    def fill_brak_rows(self, table):
        """
        Replace rows containing exactly ["BRAK"] with a full placeholder row.

        Each such row becomes a list of EXPECTED_COLUMNS copies of "BRAK".

        Args:
            table (list[list[str]]): Table rows to process.

        Returns:
            list[list[str]]: Table with "BRAK" rows expanded.
        """
        new_table = []
        for row in table:
            if len(row) == 1 and row[0].strip().upper() == "BRAK":
                new_table.append(["BRAK"] * self.expected_columns)
            else:
                new_table.append(row)
        logger.debug("Filled 'BRAK' rows: %d rows processed", len(new_table))
        return new_table

    def annotate_with_metadata(self, all_tables):
        """
        Prepend each data row with metadata columns: [kierunek, stopień, semestr].

        Single-cell rows are interpreted as metadata lines using these rules:
          1. If text contains " Stopień " or " Stopien ", split into kierunek and stopień.
          2. If text starts with "Stopień" or "Stopien", update current stopień.
          3. If text starts with "Semestr", update current semestr.
          4. Otherwise treat single-cell text as kierunek.
        Data rows (length > 1) get prepended with current metadata.

        Args:
            all_tables (list[list[list[str]]]): List of subtables to annotate.

        Returns:
            list[list[str]]: Flattened list of rows, each with metadata prepended.
        """
        new_rows = []
        current_kierunek = ""
        current_stopien = ""
        current_semestr = ""

        for table in all_tables:
            for row in table:
                if len(row) == 1:
                    text = row[0].strip()

                    if " Stopień " in text:
                        parts = text.split(" Stopień ", 1)
                        current_kierunek = parts[0].strip()
                        current_stopien = "Stopień " + parts[1].strip()
                    elif " Stopien " in text:
                        parts = text.split(" Stopien ", 1)
                        current_kierunek = parts[0].strip()
                        current_stopien = "Stopień " + parts[1].strip()
                    elif text.startswith("Stopień"):
                        current_stopien = text
                    elif text.startswith("Stopien"):
                        current_stopien = text.replace("Stopien", "Stopień", 1)
                    elif text.startswith("Semestr"):
                        current_semestr = text
                    else:
                        current_kierunek = text
                else:
                    annotated = [current_kierunek, current_stopien, current_semestr] + row
                    new_rows.append(annotated)

        logger.debug("Added metadata: %d rows ready for analysis", len(new_rows))
        return new_rows

    def finalize(self, all_tables):
        """
        Combine and postprocess all subtables, then produce the final table.

        Steps:
          1. For each subtable: merge_instructors_simple, split_if_combined_fields, fill_brak_rows.
          2. Annotate all rows with metadata via annotate_with_metadata.
          3. Take the first annotated row as the OCR-derived header; strip leading empties.
          4. Prepend ["Kierunek", "Stopień", "Semestr"] to that header.
          5. Filter remaining rows to only those with at least 11 columns (data rows).

        Args:
            all_tables (list[list[list[str]]]): List of OCR subtables.

        Returns:
            list[list[str]]: Final table with header as first row, then filtered data rows.
        """
        merged_blocks = []
        for tbl in all_tables:
            merged = self.merge_instructors_simple(tbl)
            fixed = self.split_if_combined_fields(merged)
            padded = self.fill_brak_rows(fixed)
            merged_blocks.append(padded)

        all_rows = self.annotate_with_metadata(merged_blocks)
        if not all_rows:
            logger.warning("No rows available for finalization")
            return []

        orig_header = all_rows.pop(0)
        while orig_header and orig_header[0].strip() == "":
            orig_header.pop(0)

        header = ["Kierunek", "Stopień", "Semestr"] + orig_header
        data_rows = [r for r in all_rows if len(r) >= 11]

        logger.info(
            "Finalization: OCR-derived header has %d columns, data rows = %d",
            len(header), len(data_rows)
        )
        return [header] + data_rows

    def generate_csv(self, final_table, output_path):
        """
        Write the final table to a CSV file at the specified output path.

        Creates the directory if necessary, then writes each row.

        Args:
            final_table (list[list[str]]): Table to write.
            output_path (str): Path to the CSV file.
        """
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.debug("Created directory for CSV file: %s", directory)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in final_table:
                writer.writerow(row)

        logger.info("Saved CSV: %s", output_path)
