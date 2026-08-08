import Foundation

/// The seven languages Alma speaks.
///
/// The set is closed and matches `src/lib/i18n/index.ts` exactly, because the
/// same six tags are what the *backend* writes readings in — a locale the app
/// invents is a chapter generated in a language nobody asked for, paid for, and
/// impossible to regenerate differently.
///
/// This is separate from the String Catalog. The catalog translates the
/// interface; this value travels to the server and decides what language a
/// *reading* is written in. They resolve from the same device setting and are
/// deliberately not the same type: one is a compile-time resource lookup, the
/// other is a string on the wire.
enum AppLocale: String, CaseIterable, Sendable, Identifiable, Codable {
    case en
    case es
    case de
    case it
    case fr
    case ptBR = "pt-BR"
    case ru

    var id: String { rawValue }

    /// The language's own name, as the settings screen lists it. Not localised
    /// — a language picker that renames every language into the current one is
    /// useless to somebody trying to escape a language they cannot read.
    var endonym: String {
        switch self {
        case .en: "English"
        case .es: "Español"
        case .de: "Deutsch"
        case .it: "Italiano"
        case .fr: "Français"
        case .ptBR: "Português (BR)"
        case .ru: "Русский"
        }
    }

    /// Which order the three birth-date fields are shown in.
    ///
    /// Not cosmetic, and the reason this lives on the locale rather than in a
    /// view: an American reading a European form enters 03/14 as March 14 and a
    /// European reading an American one enters it as the 3rd of the 14th. One
    /// of those two people gets somebody else's chart.
    var dateFieldOrder: [DateField] {
        switch self {
        case .en: [.day, .month, .year]
        case .es, .de, .it, .fr, .ptBR, .ru: [.day, .month, .year]
        }
    }

    enum DateField: Sendable, Hashable {
        case day
        case month
        case year
    }

    /// What the device is asking for, narrowed to what we ship.
    ///
    /// Region-aware in the one direction that matters: `pt-BR` is a locale we
    /// ship and `pt-PT` is not, so a Portuguese device gets Brazilian
    /// Portuguese rather than English — it is far closer than the fallback.
    static var current: AppLocale {
        for tag in Locale.preferredLanguages {
            let lower = tag.lowercased()
            if lower.hasPrefix("pt") { return .ptBR }
            if let match = AppLocale.allCases.first(where: {
                $0 != .ptBR && lower.hasPrefix($0.rawValue)
            }) {
                return match
            }
        }
        return .en
    }

    /// What the server said this account's locale is. Unknown tags fall back
    /// rather than throwing: an account created by an older client is not a
    /// reason to refuse to launch.
    init(serverValue: String) {
        self = AppLocale(rawValue: serverValue) ?? AppLocale(rawValue: String(serverValue.prefix(2))) ?? .en
    }
}
