import SwiftUI

/// Which plate opens which chapter.
///
/// Ported from `mobile/flutter/alma/lib/design/plates.dart`, which is the map
/// the owner dictated and the one checked against the disk: thirty-five names,
/// none spare, none missing. The keys are the chapter slugs from
/// `backend/alma/ai/chapters.py`, the only source of truth about chapters.
///
/// **The design board was drawn against different chapters.** The artist had
/// natal running as "The Sun and Its Work", "The Moon and What It Needs" —
/// chapters the engine does not have — while `karmic-axis` and `work-rhythms`
/// were left without a painting at all. Fourteen of sixteen landed with
/// certainty, four did not, and guessing them was not allowed: a wrong plate is
/// not a crooked margin but a picture about something other than what the reader
/// is reading, on a chapter they paid for. The four were settled by the owner
/// and are written down here.
///
/// **Six holes are marked `nil` honestly.** Until the art exists the chapter
/// opens on an arch with its Roman numeral, rather than on somebody else's
/// picture or on nothing. One placeholder is live — `life-path` borrows another
/// plate — and that is recorded in `docs/plates-map.md` beside the prompt that
/// replaces it.
enum AlmaPlates {

    private static let map: [SystemSlug: [String: String?]] = [
        .natal: [
            "core": "plate-shape",
            "portrait": "plate-face",
            "love": "plate-love",
            "money": "plate-money",
            "career": "plate-calling",
            "mind": "plate-speech",
            "shadow": "plate-depths",
            "roots": "plate-home",
            "karmic-axis": "plate-repeats",
            "work-rhythms": "plate-sun",
            "transformation": "plate-crisis",
            "freedom": "plate-freedom",
            "dreams": "plate-dreams",
            "circle": "plate-friends",
            "worldview": "plate-faith",
            "milestones": "plate-saturn",
        ],
        .numerology: [
            // Placeholder: another chapter's plate until "the road" is drawn.
            // Recorded in docs/plates-map.md with the prompt that replaces it.
            "life-path": "plate-soulurge",
            "birthday-number": nil,
            "personal-year": "plate-year",
            "pinnacles": "plate-eleven",
            "name": "plate-expression",
        ],
        .birthCard: [
            "personality": "plate-personality",
            "soul": "plate-soulcard",
            "year-card": "plate-yearcard",
        ],
        .transits: [
            "active": "plate-sky",
            "ahead": nil,
            "long": nil,
        ],
        .solarReturn: [
            "year-shape": "plate-solar",
            "emphasis": "plate-yeartheme",
            "contacts": "plate-yearlesson",
        ],
        .compatibility: [
            "attraction": "plate-pull",
            "friction": "plate-catches",
            "overlays": "plate-veil",
            "together": "plate-tender",
        ],
        .astrocartography: [
            "lines": "plate-lines",
            "here": "plate-whereto",
            "crossings": nil,
        ],
        // Synthesis is the system "all of it together", and one painting across
        // its four chapters is a rule here rather than a hole: four different
        // arts under "where the systems agree" and "where they part" would be
        // telling four stories instead of one.
        .synthesis: [
            "agreement": "plate-synthesis",
            "disagreement": "plate-synthesis",
            "single": "plate-synthesis",
            "whole": "plate-synthesis",
        ],
    ]

    /// The daily's plate. Not a chapter — it stands on Today.
    static let today = "plate-moon"

    static func name(_ system: SystemSlug, chapter: String) -> String? {
        map[system]?[chapter] ?? nil
    }
}

/// A plate, downloaded once and kept on disk until the app is reinstalled.
///
/// The server promises `immutable` for a year and sends an ETag, and this cache
/// exists anyway, for the reason the Flutter port's does: a hundred kilobytes
/// re-fetched every time a chapter opens is something the reader pays for on
/// mobile data, not us. Named files, and a name is never reused — a new painting
/// arrives under a new name — so there is nothing to invalidate, and the absence
/// of invalidation is a consequence of that contract rather than an oversight.
///
/// No token goes out with these requests, deliberately. `api/plates.py` serves
/// them unauthenticated because the art is not about any particular person; an
/// authenticated image would need a header on every fetch and would defeat the
/// caching it is meant to protect.
actor PlateStore {

    private let baseURL: URL
    private let session: URLSession
    private let folder: URL

    /// The fetches already running, so that two chapters sharing one plate — all
    /// four of synthesis do — make one request between them rather than two.
    private var inFlight: [String: Task<URL?, Never>] = [:]

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        self.folder = (support.first ?? URL.temporaryDirectory).appending(path: "plates")
    }

    /// The file for a plate, fetching it the first time it is wanted.
    ///
    /// `nil` means there is no picture and there will not be one — the server
    /// answered 404, or there is no network. Both are drawn the same way, with
    /// the numeral, because to a reader they are the same thing.
    func file(_ name: String) async -> URL? {
        let target = folder.appending(path: "\(name).webp")
        if FileManager.default.fileExists(atPath: target.path()) { return target }

        if let running = inFlight[name] { return await running.value }

        let task = Task<URL?, Never> { [baseURL, session, folder] in
            do {
                let url = baseURL.appending(path: "static/plates/\(name).webp")
                let (data, response) = try await session.data(from: url)
                guard let http = response as? HTTPURLResponse,
                      (200..<300).contains(http.statusCode), !data.isEmpty
                else { return nil }
                try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                // Written aside and moved into place: an interrupted download
                // must not leave half a painting on disk for the next launch to
                // mistake for a whole one.
                let partial = folder.appending(path: "\(name).webp.part")
                try? FileManager.default.removeItem(at: partial)
                try data.write(to: partial, options: .atomic)
                try? FileManager.default.removeItem(at: target)
                try FileManager.default.moveItem(at: partial, to: target)
                return target
            } catch {
                return nil
            }
        }
        inFlight[name] = task
        let result = await task.value
        inFlight[name] = nil
        return result
    }
}

/// The arch: a chapter's painting in a frame with a rounded top.
///
/// 75 above and 14 below, a gold edge and an inner stroke set in — the numbers
/// from the design canvas (`s5`: a 153×191 frame, a 150×188 picture inside it),
/// the same ones the Flutter port draws. Three states, and none of them is an
/// empty hole:
///
/// * loading — a parchment shimmer inside the arch, no spinner: a spinner says
///   "wait", and there is almost nothing to wait for here;
/// * never arrived — the chapter's Roman numeral on parchment;
/// * arrived — a 260 ms fade.
struct PlateArch: View {

    /// Where to fetch from. `nil` goes straight to the fallback, which is what
    /// a preview draws.
    let store: PlateStore?
    /// The plate's file name, or `nil` where the art has not been drawn yet.
    let plate: String?
    /// The chapter's Roman numeral — what stands in the arch instead of a
    /// picture.
    let numeral: String

    var width: CGFloat = 150
    var height: CGFloat = 188

    @State private var image: Image?
    @State private var settled = false

    /// The top is a half circle across the width; the bottom is barely rounded.
    private static let shape = UnevenRoundedRectangle(
        topLeadingRadius: 75,
        bottomLeadingRadius: 14,
        bottomTrailingRadius: 14,
        topTrailingRadius: 75,
        style: .continuous
    )

    var body: some View {
        ZStack {
            inside
                .frame(width: width, height: height)
                .clipShape(Self.shape)

            // The edge and the inner stroke sit over the picture: the frame
            // belongs to the arch rather than to what is in it, and must not
            // fade in with it.
            Self.shape
                .stroke(Color.almaGold.opacity(0.5), lineWidth: 1)
                .frame(width: width, height: height)
            Self.shape
                .stroke(Color.almaStarFill.opacity(0.4), lineWidth: 1)
                .frame(width: width - 11, height: height - 11)
        }
        .frame(width: width, height: height)
        .accessibilityHidden(true)
        .task(id: plate) {
            image = nil
            settled = false
            guard let store, let plate else {
                settled = true
                return
            }
            if let file = await store.file(plate),
               let loaded = UIImage(contentsOfFile: file.path()) {
                image = Image(uiImage: loaded)
            }
            settled = true
        }
    }

    @ViewBuilder
    private var inside: some View {
        if let image {
            image
                .resizable()
                .aspectRatio(contentMode: .fill)
                .transition(.opacity)
        } else if settled {
            numeralPlate
        } else {
            PlateShimmer()
        }
    }

    /// The fallback: the chapter's numeral on parchment.
    private var numeralPlate: some View {
        LinearGradient(
            stops: [
                .init(color: Color(hex: 0xEDE3CC), location: 0),
                .init(color: Color(hex: 0xEFE3C9), location: 0.6),
                .init(color: Color(hex: 0xDFD0AF), location: 1),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay {
            Text(verbatim: numeral)
                .font(AlmaFonts.display(34, relativeTo: .largeTitle))
                .foregroundStyle(Color.almaGoldDeep)
        }
    }
}

/// A parchment sheen while the painting travels. No spinner — a spinner promises
/// a wait, and this one is usually over before it is noticed.
private struct PlateShimmer: View {

    @State private var sweep: CGFloat = -0.5

    var body: some View {
        LinearGradient(
            colors: [Color(hex: 0xE6DCC2), Color(hex: 0xF3E9D2), Color(hex: 0xE6DCC2)],
            startPoint: UnitPoint(x: sweep - 0.6, y: 0),
            endPoint: UnitPoint(x: sweep + 0.6, y: 1)
        )
        .onAppear {
            withAnimation(.linear(duration: 1.9).repeatForever(autoreverses: false)) {
                sweep = 1.5
            }
        }
    }
}
