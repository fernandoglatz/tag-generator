// Custom Luggage/Bag Tag with QR Code v1.01 by Cristhian Valencia
//
// Author: https://makerworld.com/en/@vlycser
// Link: https://makerworld.com/en/models/710726
//
// License: CC BY-NC-ND 4.0
// https://creativecommons.org/licenses/by-nc-nd/4.0/
// Copyright (c) 2024 Cristhian Valencia
//
// Trimmed to an SVG-icon-only template: this file is rendered by
// generate-icons.py, which extrudes a single SVG icon (the tag body, text and
// QR code from the original model are not used here).

$fn = 120;

/* [Tag 🏷️] */

// Tag Thickness (mm) -- the icon is lifted to sit on top of a tag of this height.
Tag_Thickness   = 2.3;// [1:0.5:10]

// Make the icon a flat surface.
Facedown_Mode   = true;


/* [SVG Graphics ✒️] */

// Enable SVG icon
ENABLE_SVG      = true;
// SVG file ( https://www.svgrepo.com )
FILE            = "world.svg";
// SVG Thickness (mm)
SVG_THICKNESS   = 2.3;// [0.5:0.5:10]
// SVG Size (mm) -- the icon fits inside an SVG_SIZE x SVG_SIZE box.
SVG_SIZE        = 45;// [1:1:100]
// Icon aspect ratio (height/width). >1 = tall (fit by height), <=1 = wide (fit
// by width). Defaults to 1 (legacy width-fit); the generator sets the measured
// value so tall icons no longer overflow the tag.
SVG_ASPECT      = 1;
//Horizontal and vertical SVG alignment
SVG_LOCATION    = [0,10]; //[-200:0.5:200]
//Set the SVG color.
SVG_COLOR       = "#000000"; // color


/* [Experimental Configuration ⚙️] */

// Increase this value if you experience issues with the flat surface option when using Bambu Studio.
FACEDOWN_THICKNESS  = 0.004;// [0.004:0.001:0.01]

/* [Hidden] */

TAG_EXTRUDE         = Tag_Thickness;
SVG_EXTRUDE         = (Facedown_Mode)? FACEDOWN_THICKNESS:SVG_THICKNESS;

if(ENABLE_SVG){
    translate([SVG_LOCATION[0], -SVG_LOCATION[1], TAG_EXTRUDE]) color(SVG_COLOR)
        linear_extrude(height = SVG_EXTRUDE)
            resize((SVG_ASPECT > 1) ? [0,SVG_SIZE,0] : [SVG_SIZE,0,0], true)
                import (FILE, center = true);
}
