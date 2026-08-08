#!/usr/bin/env swift
//
//  Draw the app icon — and, since 7 August 2026, the two store graphics Google
//  Play demands that no build produces.
//
//  An iOS build with no icon is rejected by App Store Connect at *upload*,
//  before a human reviewer ever sees it, so nothing else in the app can be
//  tested until this file exists. It is generated rather than exported from a
//  drawing tool for the same reason `AlmaStar` is a `Shape` rather than a PNG:
//  the mark is a path on a 64-unit grid, it is defined once in
//  `DesignSystem/Brand/AlmaStar.swift` and in `src/components/brand/Star.tsx`,
//  and a third copy that somebody hand-traced is a third thing that drifts.
//
//  That argument is why the Play graphics are drawn *here* rather than by a
//  second script under `mobile/android/`. Play's icon is the same composition
//  at a different size and with an alpha channel, and its feature graphic is
//  the same night field in a wide frame — `mobile/store/SCREENSHOTS.md` §4 asks
//  for exactly that, wordless. A separate file would have been a fourth copy of
//  a nine-segment quadratic path.
//
//  The composition follows the brand book rather than inventing one:
//
//  * **Night is the canvas** — `#0A0D1C`, edge to edge, with no gradient sweep
//    across the whole square. An icon that fades to a lighter corner reads as a
//    different colour on the two home-screen backgrounds it will sit on.
//  * **One aura, off centre**, in the app's indigo, exactly where `NightSky`
//    puts it: high and to one side, never behind the subject.
//  * **One gold, aged** — the four stops of `AlmaGradient.goldLeaf`, on the
//    same diagonal, with the same struck-metal facet down the vertical arm.
//  * **A handful of stars**, small enough to survive being scaled to 40 points
//    on a home screen, placed by a fixed seed so re-running this produces the
//    same file byte for byte.
//  * **No text.** The wordmark is unreadable at 40 points and Apple's own
//    guidance is against it.
//
//  The mark sits at 62% of the canvas, which is close to Apple's own optical
//  guidance for a centred glyph and is what stops it looking like a sticker
//  floating in a square.
//
//  Every position below is written as a fraction of 1024, so the same numbers
//  place the same composition on a 512 square and on a 1024 × 500 rectangle.
//  On a non-square canvas the scale follows the *shorter* side, which is what
//  keeps the mark from being cropped by the frame.
//
//      $ swift tools/make_app_icon.swift                 # the iOS icon, in place
//      $ swift tools/make_app_icon.swift --all ../store/assets
//
//  The alpha rules are opposite on the two stores and it is not a detail:
//  App Store Connect rejects an icon that *has* an alpha channel, Play requires
//  one that *does*, and Play's feature graphic must not have one. Each output
//  below is given the right context for its destination, so the three files
//  cannot be produced from each other by resizing.
//
import AppKit
import CoreGraphics
import Foundation

func rgb(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(
        srgbRed: CGFloat((hex >> 16) & 0xFF) / 255,
        green: CGFloat((hex >> 8) & 0xFF) / 255,
        blue: CGFloat(hex & 0xFF) / 255,
        alpha: alpha
    )
}

/// Draw the whole composition onto a canvas of any shape.
///
/// - Parameter withAlpha: whether the bitmap carries an alpha channel. Every
///   pixel is opaque either way — the night fills the frame — so this only
///   decides whether the PNG is 24-bit or 32-bit, which is the thing the two
///   stores disagree about.
func render(width: Int, height: Int, withAlpha: Bool) -> CGImage {
    let w = CGFloat(width)
    let h = CGFloat(height)
    // The shorter side sets the scale: on the 1024 × 500 feature graphic the
    // mark is 310 px, centred, with night either side of it.
    let unit = min(w, h) / 1024

    guard let context = CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: CGColorSpace(name: CGColorSpace.sRGB)!,
        bitmapInfo: withAlpha
            ? CGImageAlphaInfo.premultipliedLast.rawValue
            : CGImageAlphaInfo.noneSkipLast.rawValue
    ) else { fatalError("cannot make a bitmap context") }

    // ── night ────────────────────────────────────────────────────────────
    context.setFillColor(rgb(0x0A0D1C))
    context.fill(CGRect(x: 0, y: 0, width: w, height: h))

    // ── the aura ─────────────────────────────────────────────────────────
    // `NightSky` puts one at (-110, -220) from the centre on a phone; the same
    // proportion here is up and to the left, bleeding off the corner.
    //
    // Many stops rather than three: a three-stop alpha ramp over 620 units
    // bands visibly at 8 bits per channel, and the rings are obvious on a dark
    // field.
    let auraColours = [
        rgb(0x3A3484, 0.42), rgb(0x3A3484, 0.34), rgb(0x3A3484, 0.25),
        rgb(0x3A3484, 0.17), rgb(0x3A3484, 0.10), rgb(0x3A3484, 0.045),
        rgb(0x3A3484, 0.012), rgb(0x3A3484, 0),
    ] as CFArray
    let auraCentre = CGPoint(x: 300 / 1024 * w, y: 760 / 1024 * h)
    if let aura = CGGradient(
        colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
        colors: auraColours,
        locations: [0, 0.16, 0.32, 0.47, 0.62, 0.76, 0.89, 1]
    ) {
        context.drawRadialGradient(
            aura,
            startCenter: auraCentre, startRadius: 0,
            endCenter: auraCentre, endRadius: 620 * unit,
            options: []
        )
    }

    // ── stars ────────────────────────────────────────────────────────────
    // Fixed positions rather than a random seed, so this script is reproducible
    // and so none of them lands on the mark. Sizes are large enough to survive
    // the downscale to 40 points; anything under about 3 units disappears
    // entirely and is only noise in the file.
    let stars: [(CGFloat, CGFloat, CGFloat, CGFloat)] = [
        (128, 880, 5.0, 0.85), (232, 700, 3.4, 0.55), (96, 512, 3.8, 0.45),
        (180, 300, 4.4, 0.70), (330, 176, 3.2, 0.50), (556, 96, 4.0, 0.60),
        (800, 190, 5.2, 0.80), (912, 402, 3.6, 0.50), (868, 660, 4.2, 0.65),
        (700, 872, 3.4, 0.55), (452, 940, 4.6, 0.72), (960, 852, 3.0, 0.40),
        (60, 148, 3.0, 0.38),
    ]
    for (x, y, radius, alpha) in stars {
        let cx = x / 1024 * w
        let cy = y / 1024 * h
        let r = radius * unit
        context.setFillColor(rgb(0xF6E7BC, alpha))
        context.fillEllipse(in: CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2))
    }

    // ── the mark ─────────────────────────────────────────────────────────
    // The path from `AlmaStar.StarBody`, point for point on its 64-unit grid.
    // Core Graphics puts the origin at the bottom left and the grid is written
    // for the top left, so `p` flips y.
    let markSide = min(w, h) * 0.62
    let markOrigin = CGPoint(x: (w - markSide) / 2, y: (h - markSide) / 2)

    func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
        CGPoint(
            x: markOrigin.x + x / 64 * markSide,
            y: markOrigin.y + (64 - y) / 64 * markSide
        )
    }

    let body = CGMutablePath()
    body.move(to: p(32.4, 6.4))
    body.addQuadCurve(to: p(41.2, 26.6), control: p(35.6, 22.8))
    body.addQuadCurve(to: p(57.8, 31.9), control: p(47.0, 30.0))
    body.addQuadCurve(to: p(41.0, 37.4), control: p(47.0, 34.0))
    body.addQuadCurve(to: p(32.0, 57.6), control: p(35.4, 41.0))
    body.addQuadCurve(to: p(23.0, 37.6), control: p(28.6, 41.2))
    body.addQuadCurve(to: p(6.2, 32.1), control: p(17.0, 34.2))
    body.addQuadCurve(to: p(23.2, 26.4), control: p(17.2, 29.8))
    body.addQuadCurve(to: p(32.4, 6.4), control: p(28.8, 22.6))
    body.closeSubpath()

    // A soft gold bloom under the mark. The app draws one behind Alma's
    // presence and it is what keeps the star from looking pasted onto the
    // night.
    context.saveGState()
    context.setShadow(offset: .zero, blur: 90 * unit, color: rgb(0xC9AE6B, 0.34))
    context.setFillColor(rgb(0x0A0D1C))
    context.addPath(body)
    context.fillPath()
    context.restoreGState()

    // The leaf gradient, clipped to the mark, on the same top-left →
    // bottom-right diagonal as `AlmaGradient.goldLeaf`.
    context.saveGState()
    context.addPath(body)
    context.clip()
    let leaf = [rgb(0xFBEDC4), rgb(0xE0C077), rgb(0xB3913F), rgb(0x8A6F2E)] as CFArray
    if let gradient = CGGradient(
        colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
        colors: leaf,
        locations: [0, 0.34, 0.70, 1]
    ) {
        context.drawLinearGradient(
            gradient,
            start: CGPoint(x: markOrigin.x, y: markOrigin.y + markSide),
            end: CGPoint(x: markOrigin.x + markSide, y: markOrigin.y),
            options: []
        )
    }
    context.restoreGState()

    // The facet down the vertical arm — struck metal rather than a silhouette.
    let facet = CGMutablePath()
    facet.move(to: p(32.2, 13.0))
    facet.addQuadCurve(to: p(37.6, 29.8), control: p(34.4, 26.6))
    facet.addQuadCurve(to: p(32.0, 51.0), control: p(34.2, 34.8))
    facet.addQuadCurve(to: p(26.6, 30.0), control: p(29.8, 34.8))
    facet.addQuadCurve(to: p(32.2, 13.0), control: p(30.0, 26.8))
    facet.closeSubpath()
    context.setFillColor(rgb(0x8A6F2E, 0.16))
    context.addPath(facet)
    context.fillPath()

    // The edge. Thin, dark, and the reason the mark holds an outline against a
    // bright wallpaper showing through a translucent home screen.
    context.setStrokeColor(rgb(0x7A6129))
    context.setLineWidth(0.8 / 64 * markSide)
    context.addPath(body)
    context.strokePath()

    guard let image = context.makeImage() else { fatalError("cannot render") }
    return image
}

func write(_ image: CGImage, to path: String) {
    let rep = NSBitmapImageRep(cgImage: image)
    guard let data = rep.representation(using: .png, properties: [:]) else {
        fatalError("cannot encode \(path)")
    }
    let url = URL(fileURLWithPath: path)
    try? FileManager.default.createDirectory(
        at: url.deletingLastPathComponent(), withIntermediateDirectories: true
    )
    do { try data.write(to: url) } catch { fatalError("cannot write \(path): \(error)") }
    print("wrote \(url.path) — \(image.width)×\(image.height), \(data.count) bytes")
}

// ── what to draw ─────────────────────────────────────────────────────────────

let arguments = Array(CommandLine.arguments.dropFirst())

if arguments.first == "--all" {
    // Everything, for a release. The directory is where the Play assets go;
    // the iOS icon still goes into the asset catalogue, because that one is
    // compiled into the binary rather than uploaded to a console.
    let storeDirectory = arguments.count > 1 ? arguments[1] : "../store/assets"

    write(render(width: 1024, height: 1024, withAlpha: false),
          to: "Alma/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png")
    // Play: 512 × 512, 32-bit PNG *with* alpha, at most 1024 KB.
    write(render(width: 512, height: 512, withAlpha: true),
          to: "\(storeDirectory)/play-icon-512.png")
    // Play: 1024 × 500, 24-bit PNG, *no* alpha. Required — a listing cannot be
    // published without one, and Play shows it above the screenshots.
    write(render(width: 1024, height: 500, withAlpha: false),
          to: "\(storeDirectory)/play-feature-graphic-1024x500.png")
} else {
    // The original behaviour, unchanged: one argument, or none, and the iOS
    // icon comes out where the asset catalogue expects it.
    write(render(width: 1024, height: 1024, withAlpha: false),
          to: arguments.first ?? "Alma/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png")
}
