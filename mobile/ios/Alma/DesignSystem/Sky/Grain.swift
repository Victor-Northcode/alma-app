import CoreGraphics
import SwiftUI

/// Film grain over the whole screen.
///
/// It is the smallest thing in the design language and it does the most: a flat
/// `#0A0D1C` fill on an OLED phone is a void with visible banding wherever an
/// aura meets it, and the eye reads that as "an app with a dark background". A
/// per-pixel dither at 26% in `overlay` gives the night a surface, and the
/// banding disappears because the noise is larger than the step between
/// adjacent gradient values.
///
/// Generated once into a 160×160 tile rather than shipped as an asset: a PNG of
/// noise compresses badly (it is noise), and this is forty lines of Core
/// Graphics that produce a better-distributed field than a hand-made file.
struct Grain: View {

    var opacity: Double = 0.26

    var body: some View {
        if let tile = Self.tile {
            Image(decorative: tile, scale: 1)
                .resizable(resizingMode: .tile)
                .blendMode(.overlay)
                .opacity(opacity)
                .allowsHitTesting(false)
                .ignoresSafeArea()
        }
    }

    /// Confined to the main actor because it is only ever read from a view
    /// body, and that is what lets a `CGImage` — which is not `Sendable` — be a
    /// stored static without an unsafe opt-out.
    @MainActor private static let tile: CGImage? = makeTile(side: 160)

    private static func makeTile(side: Int) -> CGImage? {
        var bytes = [UInt8](repeating: 0, count: side * side)
        var rng = SkyRandom(seed: 0x4772_6169_6E00)
        for index in bytes.indices {
            // Mid-grey ± 40. Centred on 128 because `overlay` treats 128 as the
            // identity: a tile centred anywhere else would lighten or darken
            // the whole screen instead of only texturing it.
            bytes[index] = UInt8(clamping: 128 + Int(rng.between(-40, 40)))
        }

        guard
            let provider = CGDataProvider(data: Data(bytes) as CFData),
            let image = CGImage(
                width: side,
                height: side,
                bitsPerComponent: 8,
                bitsPerPixel: 8,
                bytesPerRow: side,
                space: CGColorSpaceCreateDeviceGray(),
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue),
                provider: provider,
                decode: nil,
                shouldInterpolate: false,
                intent: .defaultIntent
            )
        else {
            // A nil tile means no grain, which is a slightly flatter night and
            // nothing worse. There is no fallback worth writing.
            return nil
        }
        return image
    }
}
