import Foundation

/// An arbitrary piece of JSON, decoded without being modelled.
///
/// It exists for exactly one field and its relatives: `CalcResult.data`, which
/// the backend types as `Record<string, unknown>` because the eight systems
/// return eight entirely different shapes — a natal chart's houses and angles, a
/// numerology reading's reduced integers, an astrocartography line list. There
/// is no honest common type, and inventing one would mean this file has to be
/// edited every time the engine gains a field.
///
/// The alternative that was rejected: eight `Codable` structs, one per system,
/// switched on `CalcResult.system`. That is the right thing to do *in the screen
/// that renders one system* — and the screens agents can do it, by calling
/// `decode(_:)` below on the branch they care about. It is the wrong thing to do
/// in the shared client, which would then fail to decode a response it does not
/// need to understand.
enum JSONValue: Sendable, Hashable, Codable {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    init(from decoder: any Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "not JSON this decoder recognises"
            )
        }
    }

    func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .null: try container.encodeNil()
        case .bool(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        }
    }

    // MARK: — reading it

    /// Subscript into an object. Returns `nil` rather than `.null` for a
    /// missing key, so that "absent" and "explicitly null" stay distinguishable
    /// — the engine uses `null` to mean *computed and empty*, which is not the
    /// same as *not computed*.
    subscript(key: String) -> JSONValue? {
        if case .object(let dictionary) = self { return dictionary[key] }
        return nil
    }

    subscript(index: Int) -> JSONValue? {
        if case .array(let items) = self, items.indices.contains(index) { return items[index] }
        return nil
    }

    var stringValue: String? {
        if case .string(let value) = self { return value }
        return nil
    }

    var doubleValue: Double? {
        if case .number(let value) = self { return value }
        return nil
    }

    var intValue: Int? {
        if case .number(let value) = self { return Int(value) }
        return nil
    }

    var boolValue: Bool? {
        if case .bool(let value) = self { return value }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case .array(let items) = self { return items }
        return nil
    }

    var objectValue: [String: JSONValue]? {
        if case .object(let dictionary) = self { return dictionary }
        return nil
    }

    /// Re-decode a subtree into a real type. This is how a screen that *does*
    /// know the shape of one system's `data` gets a struct out of it, without
    /// the shared client having to know about that struct.
    ///
    /// ```swift
    /// struct NatalData: Decodable { let houses: [House] }
    /// let natal = try result.data.decode(NatalData.self)
    /// ```
    func decode<T: Decodable>(_ type: T.Type) throws -> T {
        let data = try JSONEncoder().encode(self)
        return try JSONDecoder().decode(T.self, from: data)
    }
}
