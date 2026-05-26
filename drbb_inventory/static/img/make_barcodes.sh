#!/bin/sh

# Generate the barcode in PostScript
barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b -n > barcodes_actions_barcode.ps << BARCODES
OBTQCCH
OBTMQCH
BARCODES

# Create the header text (label above barcode)
cat > barcodes_actions_header.ps << HEADER
/showTitle { /Helvetica findfont 12 scalefont setfont moveto show } def
(QUALITY CHECK) 89 768 showTitle
(INITIATE QUALITY CHECK) 348 768 showTitle
HEADER

cat barcodes_actions_header.ps barcodes_actions_barcode.ps | ps2pdf - - > barcodes_actions.pdf
rm barcodes_actions_header.ps barcodes_actions_barcode.ps
