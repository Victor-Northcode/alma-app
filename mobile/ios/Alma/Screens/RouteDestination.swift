import SwiftUI

/// Route → screen. The one seam between the shell and the screens.
///
/// **This file is the screens' half of the contract, and it is meant to be
/// edited.** `RootView` never changes when a screen arrives; this switch does.
/// The split exists so three agents can add screens at once without any of them
/// touching navigation, presentation, safe areas or the tab bar.
///
/// The rule for whoever fills it in: a case returns a screen and nothing else.
/// No fetching here, no state, no `if session.hasBirthData` — a screen decides
/// what it is when it does not have data, because only the screen knows what it
/// should say instead.
struct RouteDestination: View {

    let route: Route

    var body: some View {
        switch route {
        case .system(let system):
            SystemScreen(system: system)

        case .chapter(let system, let chapter):
            ChapterScreen(system: system, chapter: chapter)

        case .people:
            PeopleScreen()

        case .addPerson:
            AddPersonScreen()

        case .thread(let id):
            ThreadScreen(threadID: id)

        case .offer(let system):
            OfferScreen(system: system)

        case .signIn:
            SignInScreen()

        case .legal(let document):
            LegalScreen(document: document)
        }
    }
}
