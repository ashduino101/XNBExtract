# XNBExtract
Extracts assets from XNB files

## How to use
Run `xnb_extract.py` from your terminal with the input file.

Arguments:
 - `-o | --output`: Output directory for resources, defaults to "xnb_output"
 - `-z | --gzipped`: GZip-decompresses the input file before processing

Example usage:
```shell
python3 ./xnb_extract.py MyXNBFile.xnb.gz -o output -z
```

## Requirements
 - A recent version of Python 3 (preferably 3.9-3.11)
 - Package `Pillow` (for image extraction)

## Limitations
This extractor does not support reflective references, 
as it is written in Python. If you would like to add 
your own types, add a reader to the `ObjectReader` class.
