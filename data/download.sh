#!/usr/bin/env bash
# UCI Online Retail (Chen, 2015; DOI 10.24432/C5BW33), 541,909 rows, via the Databricks
# "Spark: The Definitive Guide" mirror. Checksum verified so every run uses identical data.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
curl -sSL -o raw/online_retail.csv \
  https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv
echo "a2f79bbdd4463df6db8a3f5a50b9c980ae8f645a370bf5e2c0d6097f9e817b05  raw/online_retail.csv" | sha256sum -c -
