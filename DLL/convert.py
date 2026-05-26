import re
import os
import glob
import pandas as pd
from collections import defaultdict
import sys

try:

    # =========================================
    # CONFIG
    # =========================================

    # detect running dari exe atau python biasa
    if getattr(sys, 'frozen', False):

        # jika exe
        BASE_DIR = os.path.dirname(sys.executable)

    else:

        # jika python biasa
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # folder input txt
    input_folder = os.path.join(
        BASE_DIR,
        "download"
    )

    # folder output csv
    output_folder = os.path.join(
        BASE_DIR,
        "result",
        "va",
        "bca"
    )

    # create output folder jika belum ada
    os.makedirs(output_folder, exist_ok=True)

    # =========================================
    # REGEX TRANSAKSI
    # =========================================

    transaction_pattern = re.compile(
        r'^\s*(\d+)\s+'                  # No
        r'(\d+)\s+'                      # No pelanggan
        r'(.+?)\s+'                      # Nama pelanggan
        r'(IDR)\s+'
        r'([\d,]+\.\d{2})\s+'            # Nilai transaksi
        r'(\d{2}/\d{2}/\d{2})\s+'        # Tanggal transaksi
        r'(\d{2}:\d{2}:\d{2})\s+'
        r'(\w+)\s+'                      # Lokasi
        r'(\S+)\s+'                      # Keterangan1
        r'(\S+)\s*$'
    )

    # =========================================
    # LIST FILE TXT
    # =========================================

    txt_files = glob.glob(
        os.path.join(input_folder, "*.txt")
    )

    txt_files.extend(
        glob.glob(
            os.path.join(input_folder, "*.TXT")
        )
    )

    # remove duplicate
    txt_files = list(set(txt_files))

    # sort file
    txt_files.sort()

    # jika tidak ada file
    if not txt_files:

        print("Tidak ada file txt ditemukan")
        raise Exception("Folder download kosong")

    # =========================================
    # SUMMARY LOG
    # =========================================

    summary_messages = []

    # =========================================
    # PROCESS FILES
    # =========================================

    for txt_file in txt_files:

        filename = os.path.basename(txt_file)

        # =========================================
        # VALIDASI FILENAME
        # =========================================

        if not filename.startswith("R-5401_20808_") \
           or not filename.endswith("_rpt.txt"):

            summary_messages.append(
                f"SKIP INVALID : {filename}"
            )

            continue

        # =========================================
        # AMBIL TANGGAL REPORT
        # =========================================

        report_date = filename.split("_")[2]

        # =========================================
        # OUTPUT FILE UTAMA
        # =========================================

        main_csv_name = f"VABCA_{report_date}.csv"

        main_csv_path = os.path.join(
            output_folder,
            main_csv_name
        )

        # =========================================
        # SKIP JIKA SUDAH ADA
        # =========================================

        if os.path.exists(main_csv_path):

            summary_messages.append(
                f"SKIP : {main_csv_name}"
            )

            continue

        # =========================================
        # GROUP TRANSACTION PER TANGGAL
        # =========================================

        grouped_transactions = defaultdict(list)

        with open(txt_file, 'r', encoding='utf-8') as file:

            for line in file:

                match = transaction_pattern.match(line)

                if match:

                    # =========================================
                    # RAW DATE
                    # =========================================

                    raw_date = match.group(6)

                    # =========================================
                    # AMBIL WAKTU TRANSAKSI
                    # =========================================

                    raw_time = match.group(7)

                    # =========================================
                    # FORMAT YYYY-MM-DD HH:MM:SS
                    # =========================================

                    iso_date = (
                        "20" + raw_date[6:8] + "-" +
                        raw_date[3:5] + "-" +
                        raw_date[0:2] + " " +
                        raw_time
                    )

                    # =========================================
                    # FORMAT YYYYMMDD
                    # =========================================

                    trx_date = (
                        "20" + raw_date[6:8] +
                        raw_date[3:5] +
                        raw_date[0:2]
                    )

                    # =========================================
                    # STORE DATA
                    # =========================================

                    grouped_transactions[trx_date].append({

                        "NO.PELANGGAN/NO.TXN":
                            "20808" + match.group(2),

                        "NAMA PELANGGAN":
                            match.group(3).strip(),

                        "NILAI TRANSAKSI":
                            match.group(5)
                            .replace(",", "")
                            .replace(".00", ""),

                        "TGL. TXN":
                            iso_date,

                        "LOKASI":
                            match.group(8),

                        "KETERANGAN1":
                            match.group(9)

                    })

        # =========================================
        # TRACK MOVE STATUS
        # =========================================

        moved_to_other_date = False
        main_date_has_transaction = False

        # =========================================
        # EXPORT CSV
        # =========================================

        for trx_date, rows in grouped_transactions.items():

            # =========================================
            # FINAL ROWS + RESET NOMOR
            # =========================================

            final_rows = []

            for index, row in enumerate(rows, start=1):

                final_row = {
                    "No": index
                }

                final_row.update(row)

                final_rows.append(final_row)

            # =========================================
            # DATAFRAME
            # =========================================

            df = pd.DataFrame(final_rows)

            # =========================================
            # OUTPUT CSV
            # =========================================

            output_csv_name = f"VABCA_{trx_date}.csv"

            output_csv_path = os.path.join(
                output_folder,
                output_csv_name
            )

            # =========================================
            # APPEND EXISTING FILE
            # =========================================

            if os.path.exists(output_csv_path) \
               and output_csv_path != main_csv_path:

                existing_df = pd.read_csv(
                    output_csv_path,
                    dtype=str
                )

                combined_df = pd.concat(
                    [existing_df, df],
                    ignore_index=True
                )

                # reset nomor ulang
                combined_df["No"] = range(
                    1,
                    len(combined_df) + 1
                )

                combined_df.to_csv(
                    output_csv_path,
                    index=False
                )

            else:

                df.to_csv(
                    output_csv_path,
                    index=False
                )

            # =========================================
            # DETECT MOVE DATE
            # =========================================

            if trx_date != report_date:

                moved_to_other_date = True

                summary_messages.append(
                    f"MOVE : {main_csv_name} -> {output_csv_name}"
                )

            else:

                main_date_has_transaction = True

                moved_to_other_date = True

                summary_messages.append(
                    f"MOVE : {main_csv_name} -> {output_csv_name}"
                )

        # =========================================
        # EMPTY / CREATE STATUS
        # =========================================

        if main_date_has_transaction:

            summary_messages.append(
                f"CREATE : {main_csv_name}"
            )

        else:

            # hapus file kosong jika sempat dibuat
            if os.path.exists(main_csv_path):
                os.remove(main_csv_path)

            summary_messages.append(
                f"EMPTY : {main_csv_name} NOT CREATED"
            )

    # =========================================
    # FINAL SUMMARY
    # =========================================

    print("\n========== SUMMARY ==========\n")

    for msg in summary_messages:
        print(msg)

    print("\nSelesai")

except Exception as e:

    print("\nERROR:")
    print(e)

finally:

    input("\nTekan Enter untuk keluar...")