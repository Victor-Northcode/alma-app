# Bundled data, and where it comes from

## `places.sqlite` — GeoNames

Built from the GeoNames `cities5000` gazetteer by `tools/build_places.py`.

> This product includes GeoNames data, licensed under
> [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
> © GeoNames, https://www.geonames.org/

A licence on the *data*, not on our source. It costs an attribution line —
this one, and the equivalent in the application's about screen — and nothing
else. The Python licence gate does not check data licences, which is exactly
why this file exists.

## `de440s.bsp` — NASA JPL

The DE440s planetary ephemeris, produced by the Jet Propulsion Laboratory.
A work of the United States government: public domain, no attribution
required. Credited anyway, because it is the reason the numbers are right.

## `chiron_2060.npz` — NASA JPL Horizons

Barycentric state vectors for asteroid 2060 Chiron, sampled every four days
from 1900 to 2100 via the JPL Horizons system and interpolated at runtime.
Public domain, as above.

Sampled rather than read from an SPK because Horizons emits data type 21 for
small bodies, which neither Skyfield nor jplephem can decode. Rather than
guess at an undocumented binary layout, the states are taken from Horizons
directly and the interpolation is proven negligible by test.
