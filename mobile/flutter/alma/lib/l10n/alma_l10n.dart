import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'alma_l10n_de.dart';
import 'alma_l10n_en.dart';
import 'alma_l10n_es.dart';
import 'alma_l10n_fr.dart';
import 'alma_l10n_it.dart';
import 'alma_l10n_pt.dart';
import 'alma_l10n_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of L
/// returned by `L.of(context)`.
///
/// Applications need to include `L.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/alma_l10n.dart';
///
/// return MaterialApp(
///   localizationsDelegates: L.localizationsDelegates,
///   supportedLocales: L.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the L.supportedLocales
/// property.
abstract class L {
  L(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static L of(BuildContext context) {
    return Localizations.of<L>(context, L)!;
  }

  static const LocalizationsDelegate<L> delegate = _LDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
    Locale('es'),
    Locale('fr'),
    Locale('it'),
    Locale('pt'),
    Locale('ru'),
  ];

  /// from Cabinet/cab.accountLabel
  ///
  /// In en, this message translates to:
  /// **'account'**
  String get cabAccountLabel;

  /// from Cabinet/cab.activeNow
  ///
  /// In en, this message translates to:
  /// **'active now'**
  String get cabActiveNow;

  /// from Cabinet/cab.addBirthData
  ///
  /// In en, this message translates to:
  /// **'Enter my birth data'**
  String get cabAddBirthData;

  /// from Cabinet/cab.allAlmaPill
  ///
  /// In en, this message translates to:
  /// **'All of Alma'**
  String get cabAllAlmaPill;

  /// from Cabinet/cab.arcana.death
  ///
  /// In en, this message translates to:
  /// **'Death'**
  String get cabArcanaDeath;

  /// from Cabinet/cab.arcana.judgement
  ///
  /// In en, this message translates to:
  /// **'Judgement'**
  String get cabArcanaJudgement;

  /// from Cabinet/cab.arcana.justice
  ///
  /// In en, this message translates to:
  /// **'Justice'**
  String get cabArcanaJustice;

  /// from Cabinet/cab.arcana.strength
  ///
  /// In en, this message translates to:
  /// **'Strength'**
  String get cabArcanaStrength;

  /// from Cabinet/cab.arcana.temperance
  ///
  /// In en, this message translates to:
  /// **'Temperance'**
  String get cabArcanaTemperance;

  /// from Cabinet/cab.arcana.the_chariot
  ///
  /// In en, this message translates to:
  /// **'The Chariot'**
  String get cabArcanaTheChariot;

  /// from Cabinet/cab.arcana.the_devil
  ///
  /// In en, this message translates to:
  /// **'The Devil'**
  String get cabArcanaTheDevil;

  /// from Cabinet/cab.arcana.the_emperor
  ///
  /// In en, this message translates to:
  /// **'The Emperor'**
  String get cabArcanaTheEmperor;

  /// from Cabinet/cab.arcana.the_empress
  ///
  /// In en, this message translates to:
  /// **'The Empress'**
  String get cabArcanaTheEmpress;

  /// from Cabinet/cab.arcana.the_fool
  ///
  /// In en, this message translates to:
  /// **'The Fool'**
  String get cabArcanaTheFool;

  /// from Cabinet/cab.arcana.the_hanged_man
  ///
  /// In en, this message translates to:
  /// **'The Hanged Man'**
  String get cabArcanaTheHangedMan;

  /// from Cabinet/cab.arcana.the_hermit
  ///
  /// In en, this message translates to:
  /// **'The Hermit'**
  String get cabArcanaTheHermit;

  /// from Cabinet/cab.arcana.the_hierophant
  ///
  /// In en, this message translates to:
  /// **'The Hierophant'**
  String get cabArcanaTheHierophant;

  /// from Cabinet/cab.arcana.the_high_priestess
  ///
  /// In en, this message translates to:
  /// **'The High Priestess'**
  String get cabArcanaTheHighPriestess;

  /// from Cabinet/cab.arcana.the_lovers
  ///
  /// In en, this message translates to:
  /// **'The Lovers'**
  String get cabArcanaTheLovers;

  /// from Cabinet/cab.arcana.the_magician
  ///
  /// In en, this message translates to:
  /// **'The Magician'**
  String get cabArcanaTheMagician;

  /// from Cabinet/cab.arcana.the_moon
  ///
  /// In en, this message translates to:
  /// **'The Moon'**
  String get cabArcanaTheMoon;

  /// from Cabinet/cab.arcana.the_star
  ///
  /// In en, this message translates to:
  /// **'The Star'**
  String get cabArcanaTheStar;

  /// from Cabinet/cab.arcana.the_sun
  ///
  /// In en, this message translates to:
  /// **'The Sun'**
  String get cabArcanaTheSun;

  /// from Cabinet/cab.arcana.the_tower
  ///
  /// In en, this message translates to:
  /// **'The Tower'**
  String get cabArcanaTheTower;

  /// from Cabinet/cab.arcana.the_world
  ///
  /// In en, this message translates to:
  /// **'The World'**
  String get cabArcanaTheWorld;

  /// from Cabinet/cab.arcana.wheel_of_fortune
  ///
  /// In en, this message translates to:
  /// **'Wheel of Fortune'**
  String get cabArcanaWheelOfFortune;

  /// from Cabinet/cab.area.body
  ///
  /// In en, this message translates to:
  /// **'Body'**
  String get cabAreaBody;

  /// from Cabinet/cab.area.love
  ///
  /// In en, this message translates to:
  /// **'Love'**
  String get cabAreaLove;

  /// from Cabinet/cab.area.money
  ///
  /// In en, this message translates to:
  /// **'Money'**
  String get cabAreaMoney;

  /// from Cabinet/cab.area.work
  ///
  /// In en, this message translates to:
  /// **'Work'**
  String get cabAreaWork;

  /// from Cabinet/cab.areaQuiet
  ///
  /// In en, this message translates to:
  /// **'Nothing exact here today.'**
  String get cabAreaQuiet;

  /// from Cabinet/cab.birthDataLabel
  ///
  /// In en, this message translates to:
  /// **'birth data'**
  String get cabBirthDataLabel;

  /// from Cabinet/cab.body.ascendant
  ///
  /// In en, this message translates to:
  /// **'Ascendant'**
  String get cabBodyAscendant;

  /// from Cabinet/cab.body.chiron
  ///
  /// In en, this message translates to:
  /// **'Chiron'**
  String get cabBodyChiron;

  /// from Cabinet/cab.body.jupiter
  ///
  /// In en, this message translates to:
  /// **'Jupiter'**
  String get cabBodyJupiter;

  /// from Cabinet/cab.body.lilith
  ///
  /// In en, this message translates to:
  /// **'Lilith'**
  String get cabBodyLilith;

  /// from Cabinet/cab.body.mars
  ///
  /// In en, this message translates to:
  /// **'Mars'**
  String get cabBodyMars;

  /// from Cabinet/cab.body.mean_node
  ///
  /// In en, this message translates to:
  /// **'North Node'**
  String get cabBodyMeanNode;

  /// from Cabinet/cab.body.mercury
  ///
  /// In en, this message translates to:
  /// **'Mercury'**
  String get cabBodyMercury;

  /// from Cabinet/cab.body.midheaven
  ///
  /// In en, this message translates to:
  /// **'Midheaven'**
  String get cabBodyMidheaven;

  /// from Cabinet/cab.body.moon
  ///
  /// In en, this message translates to:
  /// **'Moon'**
  String get cabBodyMoon;

  /// from Cabinet/cab.body.neptune
  ///
  /// In en, this message translates to:
  /// **'Neptune'**
  String get cabBodyNeptune;

  /// from Cabinet/cab.body.part_of_fortune
  ///
  /// In en, this message translates to:
  /// **'Part of Fortune'**
  String get cabBodyPartOfFortune;

  /// from Cabinet/cab.body.pluto
  ///
  /// In en, this message translates to:
  /// **'Pluto'**
  String get cabBodyPluto;

  /// from Cabinet/cab.body.saturn
  ///
  /// In en, this message translates to:
  /// **'Saturn'**
  String get cabBodySaturn;

  /// from Cabinet/cab.body.south_node
  ///
  /// In en, this message translates to:
  /// **'South Node'**
  String get cabBodySouthNode;

  /// from Cabinet/cab.body.sun
  ///
  /// In en, this message translates to:
  /// **'Sun'**
  String get cabBodySun;

  /// from Cabinet/cab.body.true_node
  ///
  /// In en, this message translates to:
  /// **'North Node'**
  String get cabBodyTrueNode;

  /// from Cabinet/cab.body.uranus
  ///
  /// In en, this message translates to:
  /// **'Uranus'**
  String get cabBodyUranus;

  /// from Cabinet/cab.body.venus
  ///
  /// In en, this message translates to:
  /// **'Venus'**
  String get cabBodyVenus;

  /// from Cabinet/cab.body.vertex
  ///
  /// In en, this message translates to:
  /// **'Vertex'**
  String get cabBodyVertex;

  /// from Cabinet/cab.calculatedWord
  ///
  /// In en, this message translates to:
  /// **'calculated'**
  String get cabCalculatedWord;

  /// from Cabinet/cab.chapters
  ///
  /// In en, this message translates to:
  /// **'chapters'**
  String get cabChapters;

  /// from Cabinet/cab.compatNeedsPerson
  ///
  /// In en, this message translates to:
  /// **'Compatibility needs a second birth. Add someone and the whole comparison is calculated free.'**
  String get cabCompatNeedsPerson;

  /// from Cabinet/cab.dataAndLegal
  ///
  /// In en, this message translates to:
  /// **'data & legal'**
  String get cabDataAndLegal;

  /// from Cabinet/cab.disclaimer
  ///
  /// In en, this message translates to:
  /// **'For self-knowledge only. Not medical, psychological, legal or financial advice, and not a prediction of events.'**
  String get cabDisclaimer;

  /// from Cabinet/cab.element.air
  ///
  /// In en, this message translates to:
  /// **'air'**
  String get cabElementAir;

  /// from Cabinet/cab.element.earth
  ///
  /// In en, this message translates to:
  /// **'earth'**
  String get cabElementEarth;

  /// from Cabinet/cab.element.fire
  ///
  /// In en, this message translates to:
  /// **'fire'**
  String get cabElementFire;

  /// from Cabinet/cab.element.water
  ///
  /// In en, this message translates to:
  /// **'water'**
  String get cabElementWater;

  /// from Cabinet/cab.exportNote
  ///
  /// In en, this message translates to:
  /// **'Everything we hold about you, as one file.'**
  String get cabExportNote;

  /// from Cabinet/cab.exportReady
  ///
  /// In en, this message translates to:
  /// **'Your file is ready.'**
  String get cabExportReady;

  /// from Cabinet/cab.fact.birthplace
  ///
  /// In en, this message translates to:
  /// **'birthplace'**
  String get cabFactBirthplace;

  /// from Cabinet/cab.fact.crossings
  ///
  /// In en, this message translates to:
  /// **'crossings'**
  String get cabFactCrossings;

  /// from Cabinet/cab.fact.element
  ///
  /// In en, this message translates to:
  /// **'element'**
  String get cabFactElement;

  /// from Cabinet/cab.fact.lines
  ///
  /// In en, this message translates to:
  /// **'lines'**
  String get cabFactLines;

  /// from Cabinet/cab.fact.return
  ///
  /// In en, this message translates to:
  /// **'return'**
  String get cabFactReturn;

  /// from Cabinet/cab.fact.yearRuler
  ///
  /// In en, this message translates to:
  /// **'year ruler'**
  String get cabFactYearRuler;

  /// from Cabinet/cab.fromYourPositions
  ///
  /// In en, this message translates to:
  /// **'Written from your own positions'**
  String get cabFromYourPositions;

  /// from Cabinet/cab.guest
  ///
  /// In en, this message translates to:
  /// **'Guest'**
  String get cabGuest;

  /// from Cabinet/cab.guestNoteApp
  ///
  /// In en, this message translates to:
  /// **'You are not signed in. Your chart lives on this phone only.'**
  String get cabGuestNoteApp;

  /// from Cabinet/cab.horoscopeLocked
  ///
  /// In en, this message translates to:
  /// **'The horoscope is written from your own chart every morning, and it comes with the plan.'**
  String get cabHoroscopeLocked;

  /// from Cabinet/cab.horoscopeOpen
  ///
  /// In en, this message translates to:
  /// **'Open the horoscope'**
  String get cabHoroscopeOpen;

  /// from Cabinet/cab.horoscopeToday
  ///
  /// In en, this message translates to:
  /// **'your horoscope today'**
  String get cabHoroscopeToday;

  /// from Cabinet/cab.house.1
  ///
  /// In en, this message translates to:
  /// **'1st house'**
  String get cabHouse1;

  /// from Cabinet/cab.house.10
  ///
  /// In en, this message translates to:
  /// **'10th house'**
  String get cabHouse10;

  /// from Cabinet/cab.house.11
  ///
  /// In en, this message translates to:
  /// **'11th house'**
  String get cabHouse11;

  /// from Cabinet/cab.house.12
  ///
  /// In en, this message translates to:
  /// **'12th house'**
  String get cabHouse12;

  /// from Cabinet/cab.house.2
  ///
  /// In en, this message translates to:
  /// **'2nd house'**
  String get cabHouse2;

  /// from Cabinet/cab.house.3
  ///
  /// In en, this message translates to:
  /// **'3rd house'**
  String get cabHouse3;

  /// from Cabinet/cab.house.4
  ///
  /// In en, this message translates to:
  /// **'4th house'**
  String get cabHouse4;

  /// from Cabinet/cab.house.5
  ///
  /// In en, this message translates to:
  /// **'5th house'**
  String get cabHouse5;

  /// from Cabinet/cab.house.6
  ///
  /// In en, this message translates to:
  /// **'6th house'**
  String get cabHouse6;

  /// from Cabinet/cab.house.7
  ///
  /// In en, this message translates to:
  /// **'7th house'**
  String get cabHouse7;

  /// from Cabinet/cab.house.8
  ///
  /// In en, this message translates to:
  /// **'8th house'**
  String get cabHouse8;

  /// from Cabinet/cab.house.9
  ///
  /// In en, this message translates to:
  /// **'9th house'**
  String get cabHouse9;

  /// from Cabinet/cab.legal.imprint
  ///
  /// In en, this message translates to:
  /// **'Imprint'**
  String get cabLegalImprint;

  /// from Cabinet/cab.legal.privacy
  ///
  /// In en, this message translates to:
  /// **'Privacy'**
  String get cabLegalPrivacy;

  /// from Cabinet/cab.legal.refunds
  ///
  /// In en, this message translates to:
  /// **'Refunds'**
  String get cabLegalRefunds;

  /// from Cabinet/cab.legal.subscriptionTerms
  ///
  /// In en, this message translates to:
  /// **'Subscription terms'**
  String get cabLegalSubscriptionTerms;

  /// from Cabinet/cab.legal.terms
  ///
  /// In en, this message translates to:
  /// **'Terms'**
  String get cabLegalTerms;

  /// from Cabinet/cab.locked
  ///
  /// In en, this message translates to:
  /// **'Unlock to read'**
  String get cabLocked;

  /// from Cabinet/cab.manageInStore
  ///
  /// In en, this message translates to:
  /// **'Manage this subscription in the App Store'**
  String get cabManageInStore;

  /// Play-вариант ключа cabManageInStore: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Manage this subscription in Google Play'**
  String get cabManageInStorePlay;

  /// from Cabinet/cab.managedByApple
  ///
  /// In en, this message translates to:
  /// **'This plan was bought in the App Store, so Apple holds the payment method and the cancellation happens there.'**
  String get cabManagedByApple;

  /// Play-вариант ключа cabManagedByApple: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'This plan was bought in Google Play, so Google holds the payment method and the cancellation happens there.'**
  String get cabManagedByGooglePlay;

  /// from Cabinet/cab.merchantLine
  ///
  /// In en, this message translates to:
  /// **'Payments processed by {p1} as merchant of record · VAT/GST included where applicable'**
  String cabMerchantLine(String p1);

  /// from Cabinet/cab.noBirthData
  ///
  /// In en, this message translates to:
  /// **'Add your birth date and I can read you.'**
  String get cabNoBirthData;

  /// from Cabinet/cab.noneActive
  ///
  /// In en, this message translates to:
  /// **'No transit is active today. That is a real result, not an empty screen.'**
  String get cabNoneActive;

  /// from Cabinet/cab.pairJoin
  ///
  /// In en, this message translates to:
  /// **'{p1} and {p2}'**
  String cabPairJoin(String p1, String p2);

  /// from Cabinet/cab.phase.first-quarter
  ///
  /// In en, this message translates to:
  /// **'first quarter'**
  String get cabPhaseFirstQuarter;

  /// from Cabinet/cab.phase.full-moon
  ///
  /// In en, this message translates to:
  /// **'full moon'**
  String get cabPhaseFullMoon;

  /// from Cabinet/cab.phase.last-quarter
  ///
  /// In en, this message translates to:
  /// **'last quarter'**
  String get cabPhaseLastQuarter;

  /// from Cabinet/cab.phase.new-moon
  ///
  /// In en, this message translates to:
  /// **'new moon'**
  String get cabPhaseNewMoon;

  /// from Cabinet/cab.phase.waning-crescent
  ///
  /// In en, this message translates to:
  /// **'waning crescent'**
  String get cabPhaseWaningCrescent;

  /// from Cabinet/cab.phase.waning-gibbous
  ///
  /// In en, this message translates to:
  /// **'waning gibbous'**
  String get cabPhaseWaningGibbous;

  /// from Cabinet/cab.phase.waxing-crescent
  ///
  /// In en, this message translates to:
  /// **'waxing crescent'**
  String get cabPhaseWaxingCrescent;

  /// from Cabinet/cab.phase.waxing-gibbous
  ///
  /// In en, this message translates to:
  /// **'waxing gibbous'**
  String get cabPhaseWaxingGibbous;

  /// from Cabinet/cab.plan.cancelFailed
  ///
  /// In en, this message translates to:
  /// **'We could not reach the payment processor, so nothing has changed. Try again in a moment.'**
  String get cabPlanCancelFailed;

  /// from Cabinet/cab.plan.cancelSubscription
  ///
  /// In en, this message translates to:
  /// **'Cancel subscription'**
  String get cabPlanCancelSubscription;

  /// from Cabinet/cab.plan.cancelWhat
  ///
  /// In en, this message translates to:
  /// **'The next charge stops. Everything you have already paid for stays open until the end of the period — cancelling is not a refund, and we are not taking anything back.'**
  String get cabPlanCancelWhat;

  /// from Cabinet/cab.plan.cancelled
  ///
  /// In en, this message translates to:
  /// **'Cancelled. Your plan stays open until {p1}.'**
  String cabPlanCancelled(String p1);

  /// from Cabinet/cab.plan.cancelledNoDate
  ///
  /// In en, this message translates to:
  /// **'Cancelled. Nothing more will be charged.'**
  String get cabPlanCancelledNoDate;

  /// from Cabinet/cab.plan.cancelling
  ///
  /// In en, this message translates to:
  /// **'Stopping the next charge…'**
  String get cabPlanCancelling;

  /// from Cabinet/cab.plan.deleteFailed
  ///
  /// In en, this message translates to:
  /// **'The account could not be deleted. Try again in a moment.'**
  String get cabPlanDeleteFailed;

  /// from Cabinet/cab.plan.deleteForever
  ///
  /// In en, this message translates to:
  /// **'Delete everything, permanently'**
  String get cabPlanDeleteForever;

  /// from Cabinet/cab.plan.deleteMismatch
  ///
  /// In en, this message translates to:
  /// **'That is not the address on this account.'**
  String get cabPlanDeleteMismatch;

  /// from Cabinet/cab.plan.deleteWarning
  ///
  /// In en, this message translates to:
  /// **'This erases your chart, your readings and your questions. Readings you paid for cannot be written again word for word.'**
  String get cabPlanDeleteWarning;

  /// from Cabinet/cab.plan.deleting
  ///
  /// In en, this message translates to:
  /// **'Deleting…'**
  String get cabPlanDeleting;

  /// from Cabinet/cab.plan.exportFailed
  ///
  /// In en, this message translates to:
  /// **'The file could not be made. Try again in a moment.'**
  String get cabPlanExportFailed;

  /// from Cabinet/cab.plan.exporting
  ///
  /// In en, this message translates to:
  /// **'Preparing your file…'**
  String get cabPlanExporting;

  /// from Cabinet/cab.plan.freeNote
  ///
  /// In en, this message translates to:
  /// **'Every calculation stays free — all eight systems. You pay only for the written chapters.'**
  String get cabPlanFreeNote;

  /// from Cabinet/cab.plan.freePlan
  ///
  /// In en, this message translates to:
  /// **'Free'**
  String get cabPlanFreePlan;

  /// from Cabinet/cab.plan.keepPlan
  ///
  /// In en, this message translates to:
  /// **'Keep my plan'**
  String get cabPlanKeepPlan;

  /// from Cabinet/cab.plan.oneTimeNote
  ///
  /// In en, this message translates to:
  /// **'Bought once.'**
  String get cabPlanOneTimeNote;

  /// from Cabinet/cab.plan.ownedPlan
  ///
  /// In en, this message translates to:
  /// **'What you own'**
  String get cabPlanOwnedPlan;

  /// from Cabinet/cab.plan.planEnded
  ///
  /// In en, this message translates to:
  /// **'Your plan ended on {p1}.'**
  String cabPlanPlanEnded(String p1);

  /// from Cabinet/cab.plan.renews
  ///
  /// In en, this message translates to:
  /// **'Renews {p1} · we email you 3 days before'**
  String cabPlanRenews(String p1);

  /// from Cabinet/cab.plan.renewsAtStore
  ///
  /// In en, this message translates to:
  /// **'Renews {p1} · Apple charges it and warns you before it does'**
  String cabPlanRenewsAtStore(String p1);

  /// from Cabinet/cab.plan.renewsNoEmail
  ///
  /// In en, this message translates to:
  /// **'Renews {p1} · add an email to be warned before it charges'**
  String cabPlanRenewsNoEmail(String p1);

  /// from Cabinet/cab.plan.runsUntil
  ///
  /// In en, this message translates to:
  /// **'Runs until {p1}. It will not renew.'**
  String cabPlanRunsUntil(String p1);

  /// from Cabinet/cab.plans.body
  ///
  /// In en, this message translates to:
  /// **'The plan keeps transits, Solar Return and compatibility live, sends the morning update, and includes 30 questions a month. The five still readings can be bought once and kept for ever.'**
  String get cabPlansBody;

  /// from Cabinet/cab.plans.cta
  ///
  /// In en, this message translates to:
  /// **'See the plans'**
  String get cabPlansCta;

  /// from Cabinet/cab.plans.title
  ///
  /// In en, this message translates to:
  /// **'Everything open, every day'**
  String get cabPlansTitle;

  /// from Cabinet/cab.pullToTurn
  ///
  /// In en, this message translates to:
  /// **'Keep pulling to open it'**
  String get cabPullToTurn;

  /// from Cabinet/cab.questionsLeft
  ///
  /// In en, this message translates to:
  /// **'Questions available: {p1}'**
  String cabQuestionsLeft(int p1);

  /// from Cabinet/cab.readFrom
  ///
  /// In en, this message translates to:
  /// **'read from'**
  String get cabReadFrom;

  /// from Cabinet/cab.readingChart
  ///
  /// In en, this message translates to:
  /// **'Reading your chart'**
  String get cabReadingChart;

  /// from Cabinet/cab.saveFile
  ///
  /// In en, this message translates to:
  /// **'Save the file'**
  String get cabSaveFile;

  /// from Cabinet/cab.settings.date
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get cabSettingsDate;

  /// from Cabinet/cab.settings.deleteAccount
  ///
  /// In en, this message translates to:
  /// **'Delete account'**
  String get cabSettingsDeleteAccount;

  /// from Cabinet/cab.settings.deleteConfirm
  ///
  /// In en, this message translates to:
  /// **'Type your email address to confirm'**
  String get cabSettingsDeleteConfirm;

  /// from Cabinet/cab.settings.deleteConfirmGuest
  ///
  /// In en, this message translates to:
  /// **'Type this code to confirm'**
  String get cabSettingsDeleteConfirmGuest;

  /// from Cabinet/cab.settings.deleteGuestNote
  ///
  /// In en, this message translates to:
  /// **'This account has no email attached. Its code is below — type it to confirm.'**
  String get cabSettingsDeleteGuestNote;

  /// from Cabinet/cab.settings.everythingMonthly
  ///
  /// In en, this message translates to:
  /// **'Everything, monthly'**
  String get cabSettingsEverythingMonthly;

  /// from Cabinet/cab.settings.exportData
  ///
  /// In en, this message translates to:
  /// **'Export my data'**
  String get cabSettingsExportData;

  /// from Cabinet/cab.settings.fullName
  ///
  /// In en, this message translates to:
  /// **'Full name at birth'**
  String get cabSettingsFullName;

  /// from Cabinet/cab.settings.interfaceLanguageAction
  ///
  /// In en, this message translates to:
  /// **'Change it in Settings'**
  String get cabSettingsInterfaceLanguageAction;

  /// from Cabinet/cab.settings.language
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get cabSettingsLanguage;

  /// from Cabinet/cab.settings.place
  ///
  /// In en, this message translates to:
  /// **'Place'**
  String get cabSettingsPlace;

  /// from Cabinet/cab.settings.plan
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get cabSettingsPlan;

  /// from Cabinet/cab.settings.time
  ///
  /// In en, this message translates to:
  /// **'Time'**
  String get cabSettingsTime;

  /// from Cabinet/cab.settings.title
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get cabSettingsTitle;

  /// from Cabinet/cab.sign.Aquarius
  ///
  /// In en, this message translates to:
  /// **'Aquarius'**
  String get cabSignAquarius;

  /// from Cabinet/cab.sign.Aries
  ///
  /// In en, this message translates to:
  /// **'Aries'**
  String get cabSignAries;

  /// from Cabinet/cab.sign.Cancer
  ///
  /// In en, this message translates to:
  /// **'Cancer'**
  String get cabSignCancer;

  /// from Cabinet/cab.sign.Capricorn
  ///
  /// In en, this message translates to:
  /// **'Capricorn'**
  String get cabSignCapricorn;

  /// from Cabinet/cab.sign.Gemini
  ///
  /// In en, this message translates to:
  /// **'Gemini'**
  String get cabSignGemini;

  /// from Cabinet/cab.sign.Leo
  ///
  /// In en, this message translates to:
  /// **'Leo'**
  String get cabSignLeo;

  /// from Cabinet/cab.sign.Libra
  ///
  /// In en, this message translates to:
  /// **'Libra'**
  String get cabSignLibra;

  /// from Cabinet/cab.sign.Pisces
  ///
  /// In en, this message translates to:
  /// **'Pisces'**
  String get cabSignPisces;

  /// from Cabinet/cab.sign.Sagittarius
  ///
  /// In en, this message translates to:
  /// **'Sagittarius'**
  String get cabSignSagittarius;

  /// from Cabinet/cab.sign.Scorpio
  ///
  /// In en, this message translates to:
  /// **'Scorpio'**
  String get cabSignScorpio;

  /// from Cabinet/cab.sign.Taurus
  ///
  /// In en, this message translates to:
  /// **'Taurus'**
  String get cabSignTaurus;

  /// from Cabinet/cab.sign.Virgo
  ///
  /// In en, this message translates to:
  /// **'Virgo'**
  String get cabSignVirgo;

  /// from Cabinet/cab.signIn
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get cabSignIn;

  /// from Cabinet/cab.status.addPerson
  ///
  /// In en, this message translates to:
  /// **'add a person'**
  String get cabStatusAddPerson;

  /// from Cabinet/cab.status.calculated
  ///
  /// In en, this message translates to:
  /// **'calculated'**
  String get cabStatusCalculated;

  /// from Cabinet/cab.status.needsTime
  ///
  /// In en, this message translates to:
  /// **'needs birth time'**
  String get cabStatusNeedsTime;

  /// from Cabinet/cab.status.notYet
  ///
  /// In en, this message translates to:
  /// **'not yet'**
  String get cabStatusNotYet;

  /// from Cabinet/cab.status.open
  ///
  /// In en, this message translates to:
  /// **'open'**
  String get cabStatusOpen;

  /// from Cabinet/cab.system.astrocartography
  ///
  /// In en, this message translates to:
  /// **'Astrocartography'**
  String get cabSystemAstrocartography;

  /// from Cabinet/cab.system.birth-card
  ///
  /// In en, this message translates to:
  /// **'Birth Card'**
  String get cabSystemBirthCard;

  /// from Cabinet/cab.system.compatibility
  ///
  /// In en, this message translates to:
  /// **'Compatibility'**
  String get cabSystemCompatibility;

  /// from Cabinet/cab.system.natal
  ///
  /// In en, this message translates to:
  /// **'Natal chart'**
  String get cabSystemNatal;

  /// from Cabinet/cab.system.numerology
  ///
  /// In en, this message translates to:
  /// **'Numerology'**
  String get cabSystemNumerology;

  /// from Cabinet/cab.system.solar-return
  ///
  /// In en, this message translates to:
  /// **'Solar return'**
  String get cabSystemSolarReturn;

  /// from Cabinet/cab.system.synthesis
  ///
  /// In en, this message translates to:
  /// **'Cross-synthesis'**
  String get cabSystemSynthesis;

  /// from Cabinet/cab.system.transits
  ///
  /// In en, this message translates to:
  /// **'Transits'**
  String get cabSystemTransits;

  /// from Cabinet/cab.unknownTime
  ///
  /// In en, this message translates to:
  /// **'birth time unknown'**
  String get cabUnknownTime;

  /// from Daily/daily.ask.body
  ///
  /// In en, this message translates to:
  /// **'One notification, at the hour you choose, on the days something in your chart is exact. About once a week. Never at night, and it can be turned off from the notification itself.'**
  String get dailyAskBody;

  /// from Daily/daily.ask.title
  ///
  /// In en, this message translates to:
  /// **'Tell me the morning it happens'**
  String get dailyAskTitle;

  /// from Daily/daily.ask.yes
  ///
  /// In en, this message translates to:
  /// **'Yes, tell me'**
  String get dailyAskYes;

  /// from Daily/daily.aspect.biquintile
  ///
  /// In en, this message translates to:
  /// **'biquintile'**
  String get dailyAspectBiquintile;

  /// from Daily/daily.aspect.conjunction
  ///
  /// In en, this message translates to:
  /// **'conjunct'**
  String get dailyAspectConjunction;

  /// from Daily/daily.aspect.opposition
  ///
  /// In en, this message translates to:
  /// **'opposite'**
  String get dailyAspectOpposition;

  /// from Daily/daily.aspect.quincunx
  ///
  /// In en, this message translates to:
  /// **'quincunx'**
  String get dailyAspectQuincunx;

  /// from Daily/daily.aspect.quintile
  ///
  /// In en, this message translates to:
  /// **'quintile'**
  String get dailyAspectQuintile;

  /// from Daily/daily.aspect.semisextile
  ///
  /// In en, this message translates to:
  /// **'semisextile'**
  String get dailyAspectSemisextile;

  /// from Daily/daily.aspect.semisquare
  ///
  /// In en, this message translates to:
  /// **'semisquare'**
  String get dailyAspectSemisquare;

  /// from Daily/daily.aspect.sesquiquadrate
  ///
  /// In en, this message translates to:
  /// **'sesquiquadrate'**
  String get dailyAspectSesquiquadrate;

  /// from Daily/daily.aspect.sextile
  ///
  /// In en, this message translates to:
  /// **'sextile'**
  String get dailyAspectSextile;

  /// from Daily/daily.aspect.square
  ///
  /// In en, this message translates to:
  /// **'square'**
  String get dailyAspectSquare;

  /// from Daily/daily.aspect.trine
  ///
  /// In en, this message translates to:
  /// **'trine'**
  String get dailyAspectTrine;

  /// from Daily/daily.contactPhrase
  ///
  /// In en, this message translates to:
  /// **'{p1} {p2} your {p3}'**
  String dailyContactPhrase(String p1, String p2, String p3);

  /// from Daily/daily.retrograde
  ///
  /// In en, this message translates to:
  /// **'retrograde'**
  String get dailyRetrograde;

  /// from Daily/daily.setting.hour
  ///
  /// In en, this message translates to:
  /// **'Arrives at'**
  String get dailySettingHour;

  /// from Daily/daily.setting.occasionally
  ///
  /// In en, this message translates to:
  /// **'Occasionally'**
  String get dailySettingOccasionally;

  /// from Daily/daily.setting.occasionally.detail
  ///
  /// In en, this message translates to:
  /// **'About once a week, when something in your chart is actually exact.'**
  String get dailySettingOccasionallyDetail;

  /// from Daily/daily.setting.off
  ///
  /// In en, this message translates to:
  /// **'Off'**
  String get dailySettingOff;

  /// from Daily/daily.setting.onlyMatters.detail
  ///
  /// In en, this message translates to:
  /// **'A few times a year. The slow ones only — the transits that last months.'**
  String get dailySettingOnlyMattersDetail;

  /// from Daily/daily.setting.onlyWhatMatters
  ///
  /// In en, this message translates to:
  /// **'Long-term transits only'**
  String get dailySettingOnlyWhatMatters;

  /// from Daily/daily.setting.quiet
  ///
  /// In en, this message translates to:
  /// **'Never between 22:00 and 08:00 in your local time zone.'**
  String get dailySettingQuiet;

  /// from Daily/daily.setting.timezone
  ///
  /// In en, this message translates to:
  /// **'Time zone'**
  String get dailySettingTimezone;

  /// from Daily/daily.setting.timezone.device
  ///
  /// In en, this message translates to:
  /// **'from your device'**
  String get dailySettingTimezoneDevice;

  /// from Daily/daily.setting.title
  ///
  /// In en, this message translates to:
  /// **'Daily updates'**
  String get dailySettingTitle;

  /// from Daily/daily.status.denied
  ///
  /// In en, this message translates to:
  /// **'Notifications are off for Alma. You can turn them on in your phone\'s settings.'**
  String get dailyStatusDenied;

  /// from Daily/daily.status.openSettings
  ///
  /// In en, this message translates to:
  /// **'Open settings'**
  String get dailyStatusOpenSettings;

  /// from Daily/daily.verified.label
  ///
  /// In en, this message translates to:
  /// **'Exact transit dates in the next 30 days'**
  String get dailyVerifiedLabel;

  /// from Journey/journey.aboutTitle
  ///
  /// In en, this message translates to:
  /// **'A little about you'**
  String get journeyAboutTitle;

  /// from Journey/journey.buildMySky
  ///
  /// In en, this message translates to:
  /// **'Build my sky'**
  String get journeyBuildMySky;

  /// from Journey/journey.capture.day
  ///
  /// In en, this message translates to:
  /// **'Day of birth'**
  String get journeyCaptureDay;

  /// from Journey/journey.capture.dayShort
  ///
  /// In en, this message translates to:
  /// **'Day'**
  String get journeyCaptureDayShort;

  /// from Journey/journey.capture.impossibleDate
  ///
  /// In en, this message translates to:
  /// **'That date does not exist. Check the day.'**
  String get journeyCaptureImpossibleDate;

  /// from Journey/journey.capture.month
  ///
  /// In en, this message translates to:
  /// **'Month of birth'**
  String get journeyCaptureMonth;

  /// from Journey/journey.capture.monthShort
  ///
  /// In en, this message translates to:
  /// **'Month'**
  String get journeyCaptureMonthShort;

  /// from Journey/journey.capture.searchPlace
  ///
  /// In en, this message translates to:
  /// **'Where were you born?'**
  String get journeyCaptureSearchPlace;

  /// from Journey/journey.capture.unknownTime
  ///
  /// In en, this message translates to:
  /// **'I don\'t know my birth time'**
  String get journeyCaptureUnknownTime;

  /// from Journey/journey.capture.year
  ///
  /// In en, this message translates to:
  /// **'Year of birth'**
  String get journeyCaptureYear;

  /// from Journey/journey.capture.yearShort
  ///
  /// In en, this message translates to:
  /// **'Year'**
  String get journeyCaptureYearShort;

  /// from Journey/journey.ceremony.1.label
  ///
  /// In en, this message translates to:
  /// **'reading system 1 of 8 · natal chart'**
  String get journeyCeremony1Label;

  /// from Journey/journey.ceremony.1.line
  ///
  /// In en, this message translates to:
  /// **'Your birth chart maps the planets and key points across twelve houses using astronomical ephemeris data.'**
  String get journeyCeremony1Line;

  /// from Journey/journey.ceremony.2.label
  ///
  /// In en, this message translates to:
  /// **'reading system 2 of 8 · numerology'**
  String get journeyCeremony2Label;

  /// from Journey/journey.ceremony.2.line
  ///
  /// In en, this message translates to:
  /// **'Numerology turns your birth date into your life-path number.'**
  String get journeyCeremony2Line;

  /// from Journey/journey.ceremony.3.label
  ///
  /// In en, this message translates to:
  /// **'reading system 3 of 8 · birth card'**
  String get journeyCeremony3Label;

  /// from Journey/journey.ceremony.3.line
  ///
  /// In en, this message translates to:
  /// **'Your birth date is matched with one of the twenty-two Major Arcana.'**
  String get journeyCeremony3Line;

  /// from Journey/journey.ceremony.4.label
  ///
  /// In en, this message translates to:
  /// **'reading system 4 of 8 · transits'**
  String get journeyCeremony4Label;

  /// from Journey/journey.ceremony.4.line
  ///
  /// In en, this message translates to:
  /// **'Current transits compare today’s planet positions with your birth chart.'**
  String get journeyCeremony4Line;

  /// from Journey/journey.ceremony.5.label
  ///
  /// In en, this message translates to:
  /// **'reading system 5 of 8 · compatibility'**
  String get journeyCeremony5Label;

  /// from Journey/journey.ceremony.5.line
  ///
  /// In en, this message translates to:
  /// **'Add another person to compare your two birth charts.'**
  String get journeyCeremony5Line;

  /// from Journey/journey.ceremony.6.label
  ///
  /// In en, this message translates to:
  /// **'reading system 6 of 8 · solar return'**
  String get journeyCeremony6Label;

  /// from Journey/journey.ceremony.6.line
  ///
  /// In en, this message translates to:
  /// **'A yearly chart based on the moment the Sun returns to its birth position.'**
  String get journeyCeremony6Line;

  /// from Journey/journey.ceremony.7.label
  ///
  /// In en, this message translates to:
  /// **'reading system 7 of 8 · astrocartography'**
  String get journeyCeremony7Label;

  /// from Journey/journey.ceremony.7.line
  ///
  /// In en, this message translates to:
  /// **'A world map of planetary lines calculated from your birth time and place.'**
  String get journeyCeremony7Line;

  /// from Journey/journey.ceremony.8.label
  ///
  /// In en, this message translates to:
  /// **'reading system 8 of 8 · cross-synthesis'**
  String get journeyCeremony8Label;

  /// from Journey/journey.ceremony.8.line
  ///
  /// In en, this message translates to:
  /// **'Nine life areas compared across your birth chart, numerology and Tarot Birth Card.'**
  String get journeyCeremony8Line;

  /// from Journey/journey.close
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get journeyClose;

  /// from Journey/journey.continueCta
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get journeyContinueCta;

  /// from Journey/journey.dateSub
  ///
  /// In en, this message translates to:
  /// **'The date alone already gives three systems.'**
  String get journeyDateSub;

  /// from Journey/journey.dateTitle
  ///
  /// In en, this message translates to:
  /// **'When were you born?'**
  String get journeyDateTitle;

  /// from Journey/journey.genderFemale
  ///
  /// In en, this message translates to:
  /// **'Female'**
  String get journeyGenderFemale;

  /// from Journey/journey.genderMale
  ///
  /// In en, this message translates to:
  /// **'Male'**
  String get journeyGenderMale;

  /// from Journey/journey.genderSkip
  ///
  /// In en, this message translates to:
  /// **'Prefer not to say'**
  String get journeyGenderSkip;

  /// from Journey/journey.hourLabel
  ///
  /// In en, this message translates to:
  /// **'Hour'**
  String get journeyHourLabel;

  /// from Journey/journey.lockedWithoutTime
  ///
  /// In en, this message translates to:
  /// **'Houses, solar return and map stay locked'**
  String get journeyLockedWithoutTime;

  /// from Journey/journey.minuteLabel
  ///
  /// In en, this message translates to:
  /// **'Min'**
  String get journeyMinuteLabel;

  /// from Journey/journey.namePlaceholder
  ///
  /// In en, this message translates to:
  /// **'Sofia'**
  String get journeyNamePlaceholder;

  /// from Journey/journey.nameSub
  ///
  /// In en, this message translates to:
  /// **'Nothing is saved yet.'**
  String get journeyNameSub;

  /// from Journey/journey.nameTitle
  ///
  /// In en, this message translates to:
  /// **'What should I call you?'**
  String get journeyNameTitle;

  /// V0 · quiz.interest_title — заголовок шага «что сейчас важнее всего», жёсткий перенос холста
  ///
  /// In en, this message translates to:
  /// **'What matters most right now?'**
  String get quizInterestTitle;

  /// V0 · quiz.interest_note — подпись; обещание «можно поменять» держит настройка интереса
  ///
  /// In en, this message translates to:
  /// **'Alma starts where you are looking. You can change it later.'**
  String get quizInterestNote;

  /// V0 · quiz.interest_love
  ///
  /// In en, this message translates to:
  /// **'Love and relationships'**
  String get quizInterestLove;

  /// V0 · quiz.interest_money
  ///
  /// In en, this message translates to:
  /// **'Money and my path'**
  String get quizInterestMoney;

  /// V0 · quiz.interest_self
  ///
  /// In en, this message translates to:
  /// **'Understanding myself'**
  String get quizInterestSelf;

  /// V0 · quiz.interest_future
  ///
  /// In en, this message translates to:
  /// **'What lies ahead'**
  String get quizInterestFuture;

  /// from Journey/journey.placeSub
  ///
  /// In en, this message translates to:
  /// **'City is enough.'**
  String get journeyPlaceSub;

  /// from Journey/journey.placeTitle
  ///
  /// In en, this message translates to:
  /// **'Where were you born?'**
  String get journeyPlaceTitle;

  /// from Journey/journey.timeTitle
  ///
  /// In en, this message translates to:
  /// **'What time were you born?'**
  String get journeyTimeTitle;

  /// from Localizable/cabinet.back
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get cabinetBack;

  /// from Localizable/push.daily.conjunction
  ///
  /// In en, this message translates to:
  /// **'{p1} meets your {p2} at {p3}.'**
  String pushDailyConjunction(String p1, String p2, String p3);

  /// from Localizable/push.daily.entering.conjunction
  ///
  /// In en, this message translates to:
  /// **'{p1} is coming to your {p2}. In orb from today.'**
  String pushDailyEnteringConjunction(String p1, String p2);

  /// from Localizable/push.daily.entering.opposition
  ///
  /// In en, this message translates to:
  /// **'{p1} is coming to oppose your {p2}. In orb from today.'**
  String pushDailyEnteringOpposition(String p1, String p2);

  /// from Localizable/push.daily.entering.sextile
  ///
  /// In en, this message translates to:
  /// **'{p1} is coming to sextile your {p2}. In orb from today.'**
  String pushDailyEnteringSextile(String p1, String p2);

  /// from Localizable/push.daily.entering.square
  ///
  /// In en, this message translates to:
  /// **'{p1} is coming to square your {p2}. In orb from today.'**
  String pushDailyEnteringSquare(String p1, String p2);

  /// from Localizable/push.daily.entering.trine
  ///
  /// In en, this message translates to:
  /// **'{p1} is coming to trine your {p2}. In orb from today.'**
  String pushDailyEnteringTrine(String p1, String p2);

  /// from Localizable/push.daily.opposition
  ///
  /// In en, this message translates to:
  /// **'{p1} opposes your {p2} at {p3}.'**
  String pushDailyOpposition(String p1, String p2, String p3);

  /// from Localizable/push.daily.sextile
  ///
  /// In en, this message translates to:
  /// **'{p1} sextiles your {p2} at {p3}.'**
  String pushDailySextile(String p1, String p2, String p3);

  /// from Localizable/push.daily.square
  ///
  /// In en, this message translates to:
  /// **'{p1} squares your {p2} at {p3}.'**
  String pushDailySquare(String p1, String p2, String p3);

  /// from Localizable/push.daily.title
  ///
  /// In en, this message translates to:
  /// **'Exact today'**
  String get pushDailyTitle;

  /// from Localizable/push.daily.trine
  ///
  /// In en, this message translates to:
  /// **'{p1} trines your {p2} at {p3}.'**
  String pushDailyTrine(String p1, String p2, String p3);

  /// from Localizable/state.accountDeleted
  ///
  /// In en, this message translates to:
  /// **'This account has been deleted. Nothing of it is kept.'**
  String get stateAccountDeleted;

  /// from Localizable/state.loadingShort
  ///
  /// In en, this message translates to:
  /// **'One moment'**
  String get stateLoadingShort;

  /// from Localizable/state.offline
  ///
  /// In en, this message translates to:
  /// **'Alma is not answering right now. Nothing here is guessed, so there is nothing to show until she does.'**
  String get stateOffline;

  /// from Localizable/state.retry
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get stateRetry;

  /// from Localizable/state.unavailable
  ///
  /// In en, this message translates to:
  /// **'Something on our side is not working. It is not you, and it is not your chart.'**
  String get stateUnavailable;

  /// W6 карточка 2 · state.unbound_title — заголовок экрана привязки оплаченной проверки пары
  ///
  /// In en, this message translates to:
  /// **'Who is this reading for?'**
  String get stateUnboundTitle;

  /// W6 карточка 2 · state.unbound_note — подпись: деньги на месте, выбери человека
  ///
  /// In en, this message translates to:
  /// **'The payment went through but arrived without a name attached. Choose the person and it opens.'**
  String get stateUnboundNote;

  /// from Localizable/state.writing
  ///
  /// In en, this message translates to:
  /// **'Writing this chapter…'**
  String get stateWriting;

  /// from Localizable/tab.alma
  ///
  /// In en, this message translates to:
  /// **'Alma'**
  String get tabAlma;

  /// from Localizable/tab.settings
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get tabSettings;

  /// from Localizable/tab.systems
  ///
  /// In en, this message translates to:
  /// **'My systems'**
  String get tabSystems;

  /// from Localizable/tab.today
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get tabToday;

  /// from Paywall/paywall.doorNote
  ///
  /// In en, this message translates to:
  /// **'One payment.'**
  String get paywallDoorNote;

  /// from Paywall/paywall.manageNote
  ///
  /// In en, this message translates to:
  /// **'Plans bought in the app are cancelled in your Apple ID settings, not here.'**
  String get paywallManageNote;

  /// Play-вариант ключа paywallManageNote: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Plans bought in the app are cancelled in your Google Play subscriptions, not here.'**
  String get paywallManageNotePlay;

  /// from Paywall/paywall.monthlyNote
  ///
  /// In en, this message translates to:
  /// **'Transits, Solar Return and compatibility while they move, plus 30 questions a month. Renews until you cancel.'**
  String get paywallMonthlyNote;

  /// from Paywall/paywall.monthlyTitle
  ///
  /// In en, this message translates to:
  /// **'Everything live, monthly'**
  String get paywallMonthlyTitle;

  /// from Paywall/paywall.notNow
  ///
  /// In en, this message translates to:
  /// **'Not now'**
  String get paywallNotNow;

  /// from Paywall/paywall.notVerified
  ///
  /// In en, this message translates to:
  /// **'That purchase could not be verified, so nothing has been opened. If Apple charged you, write to us and we will sort it out.'**
  String get paywallNotVerified;

  /// from Paywall/paywall.offline
  ///
  /// In en, this message translates to:
  /// **'Alma is not answering right now, so the purchase could not be confirmed. It will open by itself once she does.'**
  String get paywallOffline;

  /// from Paywall/paywall.ownedAll
  ///
  /// In en, this message translates to:
  /// **'Everything is open. All forty-one chapters are yours.'**
  String get paywallOwnedAll;

  /// from Paywall/paywall.pending
  ///
  /// In en, this message translates to:
  /// **'Waiting for approval. Nothing has been charged, and this opens by itself the moment it is approved.'**
  String get paywallPending;

  /// from Paywall/paywall.pitchPlan1
  ///
  /// In en, this message translates to:
  /// **'The subscription keeps the three living systems written; the five still readings can be bought once and stay yours for ever.'**
  String get paywallPitchPlan1;

  /// from Paywall/paywall.pitchPlan2
  ///
  /// In en, this message translates to:
  /// **'Transits and Solar Return update as the sky changes; compatibility updates when you compare another person.'**
  String get paywallPitchPlan2;

  /// from Paywall/paywall.pitchPlan3
  ///
  /// In en, this message translates to:
  /// **'30 questions for Alma each month.'**
  String get paywallPitchPlan3;

  /// from Paywall/paywall.privacy
  ///
  /// In en, this message translates to:
  /// **'Privacy Policy'**
  String get paywallPrivacy;

  /// from Paywall/paywall.restore
  ///
  /// In en, this message translates to:
  /// **'Restore purchases'**
  String get paywallRestore;

  /// from Paywall/paywall.restored
  ///
  /// In en, this message translates to:
  /// **'Restored. Everything you bought is open again.'**
  String get paywallRestored;

  /// from Paywall/paywall.restoredNone
  ///
  /// In en, this message translates to:
  /// **'The App Store has nothing to restore for this Apple ID.'**
  String get paywallRestoredNone;

  /// Play-вариант ключа paywallRestoredNone: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Google Play has nothing to restore for this account.'**
  String get paywallRestoredNonePlay;

  /// from Paywall/paywall.restoring
  ///
  /// In en, this message translates to:
  /// **'Asking the App Store…'**
  String get paywallRestoring;

  /// Play-вариант ключа paywallRestoring: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Asking Google Play…'**
  String get paywallRestoringPlay;

  /// from Paywall/paywall.storeUnavailable
  ///
  /// In en, this message translates to:
  /// **'The App Store is not answering. Nothing here can be bought until it does — and nothing you already own has changed.'**
  String get paywallStoreUnavailable;

  /// Play-вариант ключа paywallStoreUnavailable: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Google Play is not answering. Nothing here can be bought until it does — and nothing you already own has changed.'**
  String get paywallStoreUnavailablePlay;

  /// from Paywall/paywall.subscriptionTerms
  ///
  /// In en, this message translates to:
  /// **'Subscription terms'**
  String get paywallSubscriptionTerms;

  /// from Paywall/paywall.system.astrocartography
  ///
  /// In en, this message translates to:
  /// **'Astrocartography'**
  String get paywallSystemAstrocartography;

  /// from Paywall/paywall.system.birthCard
  ///
  /// In en, this message translates to:
  /// **'Birth Card'**
  String get paywallSystemBirthCard;

  /// from Paywall/paywall.system.compatibility
  ///
  /// In en, this message translates to:
  /// **'Compatibility'**
  String get paywallSystemCompatibility;

  /// from Paywall/paywall.system.natal
  ///
  /// In en, this message translates to:
  /// **'Natal chart'**
  String get paywallSystemNatal;

  /// from Paywall/paywall.system.numerology
  ///
  /// In en, this message translates to:
  /// **'Numerology'**
  String get paywallSystemNumerology;

  /// from Paywall/paywall.system.solarReturn
  ///
  /// In en, this message translates to:
  /// **'Solar return'**
  String get paywallSystemSolarReturn;

  /// from Paywall/paywall.system.synthesis
  ///
  /// In en, this message translates to:
  /// **'Cross-synthesis'**
  String get paywallSystemSynthesis;

  /// from Paywall/paywall.system.transits
  ///
  /// In en, this message translates to:
  /// **'Transits'**
  String get paywallSystemTransits;

  /// from Paywall/paywall.terms
  ///
  /// In en, this message translates to:
  /// **'Terms'**
  String get paywallTerms;

  /// from Paywall/paywall.verifyLater
  ///
  /// In en, this message translates to:
  /// **'Apple has taken the payment. We could not confirm it this second — it will open by itself shortly, and nothing is lost.'**
  String get paywallVerifyLater;

  /// from Paywall/paywall.withdrawn
  ///
  /// In en, this message translates to:
  /// **'Apple has taken that purchase back — refunded or revoked — so nothing is open under it.'**
  String get paywallWithdrawn;

  /// from Pill/pill.sheetCta
  ///
  /// In en, this message translates to:
  /// **'See the plans · from {price}'**
  String pillSheetCta(String price);

  /// from Pill/pill.sheetFootnote
  ///
  /// In en, this message translates to:
  /// **'One-time doors exist too · cancel any time in your Apple ID settings'**
  String get pillSheetFootnote;

  /// Play-вариант ключа pillSheetFootnote: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'One-time doors exist too · cancel any time in your Google Play subscriptions'**
  String get pillSheetFootnotePlay;

  /// from Pill/pill.sheetSub
  ///
  /// In en, this message translates to:
  /// **'Your chart is already calculated — and always free. The plan opens the writing.'**
  String get pillSheetSub;

  /// from Screens/scr.addPerson.saving
  ///
  /// In en, this message translates to:
  /// **'Saving…'**
  String get scrAddPersonSaving;

  /// from Screens/scr.chat.couldAsk
  ///
  /// In en, this message translates to:
  /// **'you could ask'**
  String get scrChatCouldAsk;

  /// from Screens/scr.chat.noChart
  ///
  /// In en, this message translates to:
  /// **'I can talk without your chart, but I would only be guessing. Give me your birth data and I can read you instead.'**
  String get scrChatNoChart;

  /// from Screens/scr.chat.offline
  ///
  /// In en, this message translates to:
  /// **'I cannot reach your chart just now. Your question is still in the box — try again in a moment.'**
  String get scrChatOffline;

  /// from Screens/scr.chat.opening
  ///
  /// In en, this message translates to:
  /// **'Ask me anything about your chart. I answer from what is in it, and I tell you when it has no answer.'**
  String get scrChatOpening;

  /// from Screens/scr.chat.outOfQuestions
  ///
  /// In en, this message translates to:
  /// **'You’ve used the questions available for now. With an active subscription, you can continue; it includes 30 questions each month.'**
  String get scrChatOutOfQuestions;

  /// from Screens/scr.chat.past
  ///
  /// In en, this message translates to:
  /// **'earlier'**
  String get scrChatPast;

  /// from Screens/scr.chat.placeholder
  ///
  /// In en, this message translates to:
  /// **'Ask Alma'**
  String get scrChatPlaceholder;

  /// from Screens/scr.chat.prompt1
  ///
  /// In en, this message translates to:
  /// **'What am I like when nobody is watching?'**
  String get scrChatPrompt1;

  /// from Screens/scr.chat.prompt2
  ///
  /// In en, this message translates to:
  /// **'What is crossing my chart this week?'**
  String get scrChatPrompt2;

  /// from Screens/scr.chat.prompt3
  ///
  /// In en, this message translates to:
  /// **'Where do my systems disagree about me?'**
  String get scrChatPrompt3;

  /// from Screens/scr.chat.promptMoon
  ///
  /// In en, this message translates to:
  /// **'My Moon is in {p1}. What does it actually need?'**
  String scrChatPromptMoon(String p1);

  /// from Screens/scr.chat.promptRising
  ///
  /// In en, this message translates to:
  /// **'{p1} rising. Is that the first impression I give?'**
  String scrChatPromptRising(String p1);

  /// from Screens/scr.chat.promptSun
  ///
  /// In en, this message translates to:
  /// **'My Sun is in {p1} — what does that ask of me?'**
  String scrChatPromptSun(String p1);

  /// from Screens/scr.chat.readFromAll
  ///
  /// In en, this message translates to:
  /// **'Show the chart placements used for this answer'**
  String get scrChatReadFromAll;

  /// from Screens/scr.chat.refused
  ///
  /// In en, this message translates to:
  /// **'I could not answer that one without inventing a placement, so I did not. Ask it another way and I will try again.'**
  String get scrChatRefused;

  /// from Screens/scr.chat.silent
  ///
  /// In en, this message translates to:
  /// **'I answered that one from what I know, not from your chart.'**
  String get scrChatSilent;

  /// from Screens/scr.chat.thinking
  ///
  /// In en, this message translates to:
  /// **'Reading your chart'**
  String get scrChatThinking;

  /// from Screens/scr.chat.unavailable
  ///
  /// In en, this message translates to:
  /// **'Something on my side is not working. Your chart is untouched, and your question is still in the box.'**
  String get scrChatUnavailable;

  /// from Screens/scr.chat.untitled
  ///
  /// In en, this message translates to:
  /// **'Untitled conversation'**
  String get scrChatUntitled;

  /// from Screens/scr.chat.wentWrong
  ///
  /// In en, this message translates to:
  /// **'That did not go through. Nothing was lost — your question is still in the box.'**
  String get scrChatWentWrong;

  /// from Screens/scr.done
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get scrDone;

  /// from Screens/scr.keep
  ///
  /// In en, this message translates to:
  /// **'Keep'**
  String get scrKeep;

  /// from Screens/scr.people.change
  ///
  /// In en, this message translates to:
  /// **'Change'**
  String get scrPeopleChange;

  /// from Screens/scr.people.eyebrow
  ///
  /// In en, this message translates to:
  /// **'compatibility'**
  String get scrPeopleEyebrow;

  /// from Screens/scr.people.remove
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get scrPeopleRemove;

  /// from Screens/scr.people.removeTitle
  ///
  /// In en, this message translates to:
  /// **'Remove this person?'**
  String get scrPeopleRemoveTitle;

  /// from Screens/scr.people.removeWhat
  ///
  /// In en, this message translates to:
  /// **'Their birth goes, and so does every compatibility reading written from it. Readings you paid for cannot be written again word for word.'**
  String get scrPeopleRemoveWhat;

  /// from Screens/scr.people.unnamed
  ///
  /// In en, this message translates to:
  /// **'Unnamed'**
  String get scrPeopleUnnamed;

  /// from Screens/scr.saveAccount.body
  ///
  /// In en, this message translates to:
  /// **'Sign in to keep your chart and restore your purchases on a new phone.'**
  String get scrSaveAccountBody;

  /// from Screens/scr.saveAccount.cta
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get scrSaveAccountCta;

  /// from Screens/scr.saveAccount.later
  ///
  /// In en, this message translates to:
  /// **'Not now'**
  String get scrSaveAccountLater;

  /// from Screens/scr.saveAccount.title
  ///
  /// In en, this message translates to:
  /// **'Keep your chart'**
  String get scrSaveAccountTitle;

  /// from Screens/scr.signIn.already
  ///
  /// In en, this message translates to:
  /// **'You are already signed in. This account follows you to any phone.'**
  String get scrSignInAlready;

  /// from Screens/scr.signIn.done
  ///
  /// In en, this message translates to:
  /// **'You are signed in.'**
  String get scrSignInDone;

  /// from Screens/scr.signIn.emailPlaceholder
  ///
  /// In en, this message translates to:
  /// **'Your email address'**
  String get scrSignInEmailPlaceholder;

  /// from Screens/scr.signIn.failed
  ///
  /// In en, this message translates to:
  /// **'That did not sign you in. Nothing has changed on your account.'**
  String get scrSignInFailed;

  /// from Screens/scr.signIn.lead
  ///
  /// In en, this message translates to:
  /// **'Your chart follows you to any phone.'**
  String get scrSignInLead;

  /// from Screens/scr.signIn.linkSent
  ///
  /// In en, this message translates to:
  /// **'Check your inbox. The link signs you in and expires shortly.'**
  String get scrSignInLinkSent;

  /// from Screens/scr.signIn.orWith
  ///
  /// In en, this message translates to:
  /// **'or sign in with'**
  String get scrSignInOrWith;

  /// from Screens/scr.signIn.privacy
  ///
  /// In en, this message translates to:
  /// **'We use your address for the sign-in link and nothing else. There is no newsletter.'**
  String get scrSignInPrivacy;

  /// from Screens/scr.signIn.sendLink
  ///
  /// In en, this message translates to:
  /// **'Email me a sign-in link'**
  String get scrSignInSendLink;

  /// Короткий вариант подписи кнопки для узких экранов. Совпадает с полным везде, кроме немецкого: короче «Anmeldelink per E-Mail senden» в языке ничего нет, а в остальных сокращать нечего.
  ///
  /// In en, this message translates to:
  /// **'Email me a sign-in link'**
  String get scrSignInSendLinkShort;

  /// from Screens/scr.signIn.sending
  ///
  /// In en, this message translates to:
  /// **'Sending…'**
  String get scrSignInSending;

  /// from Screens/scr.signIn.title
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get scrSignInTitle;

  /// No description provided for @cabCompatNeedsSecond.
  ///
  /// In en, this message translates to:
  /// **'Compatibility needs a second person.'**
  String get cabCompatNeedsSecond;

  /// No description provided for @cabPeopleTitle.
  ///
  /// In en, this message translates to:
  /// **'People'**
  String get cabPeopleTitle;

  /// No description provided for @cabPeopleAdd.
  ///
  /// In en, this message translates to:
  /// **'Add a person'**
  String get cabPeopleAdd;

  /// Подпись под знаком на заставке.
  ///
  /// In en, this message translates to:
  /// **'Written in the sky before you asked.'**
  String get splashTagline;

  /// Под полем имени: где имя будет видно, а где нет.
  ///
  /// In en, this message translates to:
  /// **'Alma will greet you by it — nowhere else.'**
  String get journeyNameHint;

  /// Подзаголовок шага «о себе».
  ///
  /// In en, this message translates to:
  /// **'You can skip this. It only tunes how Alma writes to you.'**
  String get journeyAboutSkip;

  /// Оверлайн развилки перевода часов. Номера шага у неё нет: это не часть анкеты, а вопрос, который небо задаёт в ответ во время церемонии.
  ///
  /// In en, this message translates to:
  /// **'about your birth time'**
  String get dstOverline;

  /// Заголовок развилки.
  ///
  /// In en, this message translates to:
  /// **'That night, {time} happened twice'**
  String dstTitle(String time);

  /// Что произошло в ту ночь и почему выбор за человеком.
  ///
  /// In en, this message translates to:
  /// **'Clocks were set back in {city} on {date}. Alma will not flip a coin about your sky — which {time} is yours?'**
  String dstBody(String city, String date, String time);

  /// Первый из двух моментов.
  ///
  /// In en, this message translates to:
  /// **'The earlier one'**
  String get dstEarlier;

  /// Летние часы: имя зоны приходит с сервера.
  ///
  /// In en, this message translates to:
  /// **'{time} on the summer clock · {abbr}'**
  String dstEarlierSub(String time, String abbr);

  /// Второй из двух моментов.
  ///
  /// In en, this message translates to:
  /// **'The later one'**
  String get dstLater;

  /// Зимние часы и размер склейки.
  ///
  /// In en, this message translates to:
  /// **'{time} on the winter clock · {abbr}, {delta} after'**
  String dstLaterSub(String time, String abbr, String delta);

  /// Что делать тому, кто не знает. Размер склейки тот же.
  ///
  /// In en, this message translates to:
  /// **'If nobody remembers, pick either — the houses shift by {delta} and you can change it in Settings.'**
  String dstFooter(String delta);

  /// Размер склейки, когда он час. Подставляется в {delta}: захардкоженного «часом позже» быть не должно — переводы на полчаса существуют.
  ///
  /// In en, this message translates to:
  /// **'an hour'**
  String get dstDeltaHour;

  /// Размер склейки в полчаса — остров Лорд-Хау и подобные.
  ///
  /// In en, this message translates to:
  /// **'30 minutes'**
  String get dstDeltaHalfHour;

  /// from Chat/chat.readingHouse (A2 thinking, real engine stage)
  ///
  /// In en, this message translates to:
  /// **'reading your {house} house…'**
  String chatReadingHouse(String house);

  /// from Chat/chat.openingBody (A2 thinking, real engine stage)
  ///
  /// In en, this message translates to:
  /// **'opening {body}…'**
  String chatOpeningBody(String body);

  /// from Chat/chat.fromChapter (A5 chapter link)
  ///
  /// In en, this message translates to:
  /// **'Read the chapter it comes from — {chapter}'**
  String chatFromChapter(String chapter);

  /// from Chat/chat.notTemplate (A1 quiet line)
  ///
  /// In en, this message translates to:
  /// **'I answer from your chart, never from a template.'**
  String get chatNotTemplate;

  /// Подпись под ручкой вкладок в чате, кегль 9.5, и голосовая метка самой ручки — одна строка на двоих: ручку 30×3 пальцем не найти, а VoiceOver до сих пор называл кнопку никак. strings-batch2.md.
  ///
  /// In en, this message translates to:
  /// **'Swipe up for tabs'**
  String get scrChatSwipeForTabs;

  /// S23, заголовок над обещанием совместимости: экран без второго человека — приглашение, а не ошибка, и начинаться он должен с титула. strings-batch2.md.
  ///
  /// In en, this message translates to:
  /// **'Two skies, one comparison'**
  String get cabCompatTwoSkies;

  /// S23, первый из трёх пунктов о том, что будет посчитано, когда второй человек появится. strings-batch2.md.
  ///
  /// In en, this message translates to:
  /// **'Every contact between the two charts, with its exact orb'**
  String get cabCompatBulletContacts;

  /// S23, второй пункт. strings-batch2.md.
  ///
  /// In en, this message translates to:
  /// **'Where their planets land in your houses — and yours in theirs'**
  String get cabCompatBulletHouses;

  /// S23, третий пункт. strings-batch2.md.
  ///
  /// In en, this message translates to:
  /// **'The relationship\'s own chart — the sky of the two of you as one'**
  String get cabCompatBulletComposite;

  /// today-reading-spec §6 · todayReadWholeSky
  ///
  /// In en, this message translates to:
  /// **'Read the whole sky'**
  String get todayReadWholeSky;

  /// today-reading-spec §6 · todayReadMinutes
  ///
  /// In en, this message translates to:
  /// **'{n} min'**
  String todayReadMinutes(String n);

  /// today-reading-spec §6 · readerHeader
  ///
  /// In en, this message translates to:
  /// **'{date} · your sky'**
  String readerHeader(String date);

  /// today-reading-spec §6 · readerAskAboutIt
  ///
  /// In en, this message translates to:
  /// **'Ask Alma about {aspect}'**
  String readerAskAboutIt(String aspect);

  /// today-reading-spec §6 · readerTextSize
  ///
  /// In en, this message translates to:
  /// **'Text size'**
  String get readerTextSize;

  /// monetization v3 · А11 door.title · V1/V2
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one{One more chapter} other{{count} more chapters}}'**
  String paywallV3DoorTitle(int count);

  /// monetization v3 · А11 door.price · V1/V2
  ///
  /// In en, this message translates to:
  /// **'{price} · forever'**
  String paywallV3DoorPrice(String price);

  /// monetization v3 · А11 door.forever · V1/V2
  ///
  /// In en, this message translates to:
  /// **'Yours forever · no subscription'**
  String get paywallV3DoorForever;

  /// monetization v3 · А11 door.chapters_count · V1/V2/W3/W5
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one{{count} chapter} other{{count} chapters}}'**
  String paywallV3DoorChaptersCount(int count);

  /// monetization v3 · А11 door.cta · V1/V2
  ///
  /// In en, this message translates to:
  /// **'Open the whole reading · {price}'**
  String paywallV3DoorCta(String price);

  /// V1 · короткий вариант кнопки двери для узкой карточки: тот же смысл, цена обязана быть видна
  ///
  /// In en, this message translates to:
  /// **'Open it · {price}'**
  String paywallV3DoorCtaShort(Object price);

  /// monetization v3 · А11 door.bundle_link · V1
  ///
  /// In en, this message translates to:
  /// **'All five readings — {price}'**
  String paywallV3DoorBundleLink(String price);

  /// monetization v3 · А11 bundle.title · V3/V8
  ///
  /// In en, this message translates to:
  /// **'All five readings'**
  String get paywallV3BundleTitle;

  /// monetization v3 · А11 bundle.price · V3/V8
  ///
  /// In en, this message translates to:
  /// **'{price} · forever'**
  String paywallV3BundlePrice(String price);

  /// monetization v3 · А11 bundle.saving · V3/V8
  ///
  /// In en, this message translates to:
  /// **'Twenty per cent off'**
  String get paywallV3BundleSaving;

  /// monetization v3 · А11 bundle.includes · V3/V8
  ///
  /// In en, this message translates to:
  /// **'Natal · numerology · birth card · astrocartography · synthesis'**
  String get paywallV3BundleIncludes;

  /// monetization v3 · А11 bundle.cta · V3/V8
  ///
  /// In en, this message translates to:
  /// **'Open all five · {price}'**
  String paywallV3BundleCta(String price);

  /// monetization v3 · А11 pair.input_title · W2
  ///
  /// In en, this message translates to:
  /// **'Who are we reading together?'**
  String get paywallV3PairInputTitle;

  /// monetization v3 · А11 pair.input_name · W2
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get paywallV3PairInputName;

  /// monetization v3 · А11 pair.input_date · W2
  ///
  /// In en, this message translates to:
  /// **'Date of birth'**
  String get paywallV3PairInputDate;

  /// monetization v3 · А11 pair.price · V4/V5
  ///
  /// In en, this message translates to:
  /// **'{price} · forever'**
  String paywallV3PairPrice(String price);

  /// monetization v3 · А11 pair.forever · V4
  ///
  /// In en, this message translates to:
  /// **'Stays yours forever'**
  String get paywallV3PairForever;

  /// monetization v3 · А11 pair.included_badge · V4/V5
  ///
  /// In en, this message translates to:
  /// **'included in your month'**
  String get paywallV3PairIncludedBadge;

  /// monetization v3 · А11 pair.beyond_credit · V5
  ///
  /// In en, this message translates to:
  /// **'Beyond your monthly check · stays yours forever'**
  String get paywallV3PairBeyondCredit;

  /// monetization v3 · А11 pair.my_pairs_title · V5
  ///
  /// In en, this message translates to:
  /// **'My pairs'**
  String get paywallV3PairMyPairsTitle;

  /// monetization v3 · А11 pair.check_another · V5
  ///
  /// In en, this message translates to:
  /// **'Check someone else · {price}'**
  String paywallV3PairCheckAnother(String price);

  /// monetization v3 · А11 sub.title · V6
  ///
  /// In en, this message translates to:
  /// **'The sky keeps moving. Alma keeps reading it.'**
  String get paywallV3SubTitle;

  /// monetization v3 · А11 sub.price · V6/V7/V8
  ///
  /// In en, this message translates to:
  /// **'{price} / month'**
  String paywallV3SubPrice(String price);

  /// monetization v3 · А11 sub.renewal_disclosure · V6/V7/V8
  ///
  /// In en, this message translates to:
  /// **'Renews monthly · cancel any time in your Apple ID settings'**
  String get paywallV3SubRenewalDisclosure;

  /// Play-вариант ключа paywallV3SubRenewalDisclosure: Android обязан называть свой магазин своими словами
  ///
  /// In en, this message translates to:
  /// **'Renews monthly · cancel any time in Google Play'**
  String get paywallV3SubRenewalDisclosurePlay;

  /// monetization v3 · А11 sub.includes_transits · V6/V8
  ///
  /// In en, this message translates to:
  /// **'Transits and the morning horoscope, written from your chart'**
  String get paywallV3SubIncludesTransits;

  /// monetization v3 · А11 sub.includes_solar · V6/V8
  ///
  /// In en, this message translates to:
  /// **'Your solar return, rewritten each birthday'**
  String get paywallV3SubIncludesSolar;

  /// monetization v3 · А11 sub.includes_pair · V6/V8
  ///
  /// In en, this message translates to:
  /// **'One full compatibility check a month'**
  String get paywallV3SubIncludesPair;

  /// monetization v3 · А11 sub.includes_questions · V6/V8
  ///
  /// In en, this message translates to:
  /// **'Thirty questions for Alma · all five readings while active'**
  String get paywallV3SubIncludesQuestions;

  /// monetization v3 · А11 sub.forever_stays · V6/V8
  ///
  /// In en, this message translates to:
  /// **'Readings bought forever stay yours even without a subscription.'**
  String get paywallV3SubForeverStays;

  /// monetization v3 · А11 sub.cta · V6
  ///
  /// In en, this message translates to:
  /// **'All of Alma · {price} / month'**
  String paywallV3SubCta(String price);

  /// monetization v3 · А11 quota.title · V7
  ///
  /// In en, this message translates to:
  /// **'Three questions a month is where free ends'**
  String get paywallV3QuotaTitle;

  /// monetization v3 · А11 quota.cta · V7
  ///
  /// In en, this message translates to:
  /// **'Ask on · {price} / month'**
  String paywallV3QuotaCta(String price);

  /// monetization v3 · А11 plans.group_forever · V8
  ///
  /// In en, this message translates to:
  /// **'forever'**
  String get paywallV3PlansGroupForever;

  /// monetization v3 · А11 plans.group_subscription · V8
  ///
  /// In en, this message translates to:
  /// **'subscription'**
  String get paywallV3PlansGroupSubscription;

  /// monetization v3 · А11 plans.divider_note · V8
  ///
  /// In en, this message translates to:
  /// **'What you bought forever does not disappear if you cancel.'**
  String get paywallV3PlansDividerNote;

  /// monetization v3 · А11 cancel.save_title · V9
  ///
  /// In en, this message translates to:
  /// **'Take your reading with you'**
  String get paywallV3CancelSaveTitle;

  /// monetization v3 · А11 cancel.save_cta · V9
  ///
  /// In en, this message translates to:
  /// **'Keep it forever · {price}'**
  String paywallV3CancelSaveCta(String price);

  /// monetization v3 · А11 cancel.just_cancel · V9
  ///
  /// In en, this message translates to:
  /// **'Just cancel'**
  String get paywallV3CancelJustCancel;

  /// monetization v3 · А11 state.processing · W6
  ///
  /// In en, this message translates to:
  /// **'Your purchase is going through'**
  String get paywallV3StateProcessing;

  /// monetization v3 · А11 state.error_retry · W6
  ///
  /// In en, this message translates to:
  /// **'Try again now'**
  String get paywallV3StateErrorRetry;

  /// monetization v3 · А11 state.restore_done · W6
  ///
  /// In en, this message translates to:
  /// **'Restored · everything you bought is open again'**
  String get paywallV3StateRestoreDone;

  /// monetization v3 · door.plate_chapter · V2 — римская цифра собирается клиентом
  ///
  /// In en, this message translates to:
  /// **'chapter {numeral}'**
  String paywallV3DoorPlateChapter(String numeral);

  /// monetization v3 · door.title · V2 — plural + имя системы вставкой в именительном
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one{One chapter of your {system}} other{{count} chapters of your {system}}}'**
  String paywallV3DoorTitleSystem(int count, String system);

  /// monetization v3 · V2 без числа глав — на холсте не нарисовано, минимальный вариант
  ///
  /// In en, this message translates to:
  /// **'Your {system}, all of it'**
  String paywallV3DoorTitleAll(String system);

  /// monetization v3 · door.pitch · V2
  ///
  /// In en, this message translates to:
  /// **'Written from your own positions — never from a template. The calculation was always free; this is the writing.'**
  String get paywallV3DoorPitch;

  /// monetization v3 · door.cta · V2 (на V1 своя подпись — paywallV3DoorCta)
  ///
  /// In en, this message translates to:
  /// **'Unlock and read · {price}'**
  String paywallV3DoorCtaUnlock(String price);

  /// monetization v3 · plans.link · V2/V6
  ///
  /// In en, this message translates to:
  /// **'All plans'**
  String get paywallV3PlansLink;

  /// monetization v3 · sub.overline · V6
  ///
  /// In en, this message translates to:
  /// **'the living layer'**
  String get paywallV3SubOverline;

  /// monetization v3 · sub.plate_caption · V6
  ///
  /// In en, this message translates to:
  /// **'Everything that changes daily'**
  String get paywallV3SubPlateCaption;

  /// monetization v3 · quota.held · V7
  ///
  /// In en, this message translates to:
  /// **'held — will send when you continue'**
  String get paywallV3QuotaHeld;

  /// monetization v3 · quota.note · V7 — число вопросов словом, кириллица 25 (ТЗ §2)
  ///
  /// In en, this message translates to:
  /// **'Alma answers thirty a month inside the subscription — from your own placements, never from a template.'**
  String get paywallV3QuotaNote;

  /// monetization v3 · quota.also_inside · V7
  ///
  /// In en, this message translates to:
  /// **'also inside'**
  String get paywallV3QuotaAlsoInside;

  /// monetization v3 · quota.also_inside_list · V7
  ///
  /// In en, this message translates to:
  /// **'Transits and the daily horoscope · your solar return · one compatibility check a month'**
  String get paywallV3QuotaAlsoInsideList;

  /// monetization v3 · sub.renewal_disclosure_quota · V7 — третий пункт про отправку вопроса
  ///
  /// In en, this message translates to:
  /// **'Renews monthly · cancel any time · your question sends the moment it opens'**
  String get paywallV3SubRenewalDisclosureQuota;

  /// monetization v3 · plans.overline · V8
  ///
  /// In en, this message translates to:
  /// **'all plans'**
  String get paywallV3PlansOverline;

  /// monetization v3 · plans.title · V8
  ///
  /// In en, this message translates to:
  /// **'Yours forever, or everything alive'**
  String get paywallV3PlansTitle;

  /// monetization v3 · plans.one_reading · V8
  ///
  /// In en, this message translates to:
  /// **'One reading'**
  String get paywallV3PlansOneReading;

  /// monetization v3 · plans.all_five_note · V8 — 26 платных глав пяти разборов
  ///
  /// In en, this message translates to:
  /// **'Thirty-one chapters, twenty per cent off'**
  String get paywallV3PlansAllFiveNote;

  /// monetization v3 · plans.pair · V8
  ///
  /// In en, this message translates to:
  /// **'A compatibility report'**
  String get paywallV3PlansPair;

  /// monetization v3 · plans.pair_note · V8
  ///
  /// In en, this message translates to:
  /// **'Four chapters, per person, as many as you like'**
  String get paywallV3PlansPairNote;

  /// monetization v3 · sub.title_short · V8
  ///
  /// In en, this message translates to:
  /// **'All of Alma'**
  String get paywallV3SubTitleShort;

  /// monetization v3 · sub.includes_line · V8 — кириллица 25 вопросов (ТЗ §2)
  ///
  /// In en, this message translates to:
  /// **'Transits and the daily horoscope · solar return · one compatibility check a month · 30 questions · all five readings while active'**
  String get paywallV3SubIncludesLine;

  /// monetization v3 · plans.legal · V8 — сокращать нельзя, требование ревью магазинов
  ///
  /// In en, this message translates to:
  /// **'Charged to your Apple ID on confirm · the subscription renews monthly unless cancelled 24 h before the period ends · one-time purchases never renew'**
  String get paywallV3PlansLegal;

  /// monetization v3 · cancel.header · V9
  ///
  /// In en, this message translates to:
  /// **'manage subscription'**
  String get paywallV3CancelHeader;

  /// monetization v3 · cancel.card_caption · V9
  ///
  /// In en, this message translates to:
  /// **'the one you read most'**
  String get paywallV3CancelCardCaption;

  /// monetization v3 · cancel.save_fact · V9 — два plural-числа из телеметрии
  ///
  /// In en, this message translates to:
  /// **'You have opened {chapters, plural, one{this chapter} other{these {chapters} chapters}} {times, plural, one{once} other{{times} times}}. For {price} they stay readable after the subscription ends — no renewal, ever.'**
  String paywallV3CancelSaveFact(int chapters, int times, String price);

  /// monetization v3 · V9 без статистики чтения — на холсте не нарисовано
  ///
  /// In en, this message translates to:
  /// **'For {price} they stay readable after the subscription ends — no renewal, ever.'**
  String paywallV3CancelSaveFactPlain(String price);

  /// monetization v3 · cancel.note · V9
  ///
  /// In en, this message translates to:
  /// **'Cancelling opens your Apple ID settings · your subscription runs until {date}'**
  String paywallV3CancelNote(String date);

  /// monetization v3 · V9 без даты конца периода — на холсте не нарисовано
  ///
  /// In en, this message translates to:
  /// **'Cancelling opens your Apple ID settings'**
  String get paywallV3CancelNoteNoDate;

  /// monetization v3 · А11 chapter.what_rest_holds · V1 — оверлайн над чипами глав в конце бесплатной главы
  ///
  /// In en, this message translates to:
  /// **'what the rest holds'**
  String get paywallV3DoorWhatRestHolds;

  /// monetization v3 · А11 chapter.more_count · V1 — шестой, приглушённый чип: сколько глав не поместилось в пять видимых
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one{+{count} more} other{+{count} more}}'**
  String paywallV3DoorMoreCount(int count);

  /// monetization v3 · А11 door.overline · V1 — оверлайн карточки. На холсте «your natal reading»; имя системы вставкой, потому что блок поднимается у любой системы с дверью, а не только у натала
  ///
  /// In en, this message translates to:
  /// **'your {system} reading'**
  String paywallV3DoorOverline(String system);

  /// monetization v3 · А11 door.chapters_count · V1 — подпись под заголовком карточки. Счётный вариант того же ключа занят paywallV3DoorChaptersCount (V2/W3/W5), а холст просит здесь фразу, а не число; перечисление глав холста («Love, money, work, the shadow») натальное и на четырёх других системах было бы неправдой — их имена и без того стоят чипами выше
  ///
  /// In en, this message translates to:
  /// **'Every chapter written from your own positions, not from a template.'**
  String get paywallV3DoorChaptersLine;

  /// monetization v3 · door.cta · V1 без цены — магазин отвечает не мгновенно, и кнопка обязана рисоваться до его ответа: та же подпись без хвоста с ценой
  ///
  /// In en, this message translates to:
  /// **'Open the whole reading'**
  String get paywallV3DoorCtaNoPrice;

  /// monetization v3 · А11 next.overline · V3 — и он же заголовок блока-приглашения в конце последней главы
  ///
  /// In en, this message translates to:
  /// **'what next'**
  String get paywallV3WhatNextOverline;

  /// monetization v3 · V3 — единственная строка блока-приглашения; тап открывает экран «Что дальше»
  ///
  /// In en, this message translates to:
  /// **'The last chapter is read — see where it leads'**
  String get paywallV3WhatNextInviteLine;

  /// monetization v3 · V3 карточка 1 — открыть бесплатную главу следующей непрочитанной системы
  ///
  /// In en, this message translates to:
  /// **'Read the opening'**
  String get paywallV3WhatNextReadOpening;

  /// monetization v3 · А11 next.pair_title · V3
  ///
  /// In en, this message translates to:
  /// **'Check the two of you'**
  String get paywallV3WhatNextPairTitle;

  /// monetization v3 · А11 next.pair_note · V3
  ///
  /// In en, this message translates to:
  /// **'Your Venus chapter says how you attach. His date says how it lands.'**
  String get paywallV3WhatNextPairNote;

  /// monetization v3 · V3 карточка 2 — цена pair.check из магазина
  ///
  /// In en, this message translates to:
  /// **'Check someone · {price}'**
  String paywallV3WhatNextPairCta(String price);

  /// locked-chapter-spec §6 · C5 · подпись карточки совместимости в «Моих системах»
  ///
  /// In en, this message translates to:
  /// **'tap to add someone'**
  String get systemsTapToAdd;

  /// locked-chapter-spec §6 · C5 · подпись карточки, у которой ещё не открыта ни одна глава
  ///
  /// In en, this message translates to:
  /// **'read the opening'**
  String get systemsReadOpening;

  /// locked-chapter-spec §1 · C5 · сколько глав системы уже открыто
  ///
  /// In en, this message translates to:
  /// **'{open} of {total} open'**
  String systemsChaptersOpen(int open, int total);

  /// locked-chapter-spec §6 · C1 · бейдж единственной бесплатной главы продукта (натал I)
  ///
  /// In en, this message translates to:
  /// **'free'**
  String get chapterFreeBadge;

  /// locked-chapter-spec §4 · кнопка статичного разбора на самой главе. Цена внутри строки, а не приклеена кодом: точка-разделитель принадлежит переводчику, и в языке, где её место другое, она сдвинется вместе с текстом
  ///
  /// In en, this message translates to:
  /// **'Unlock and read · {price}'**
  String chapterUnlockCta(String price);

  /// locked-chapter-spec §4 · природа покупки под кнопкой статичного разбора. Слово «продление» здесь запрещено
  ///
  /// In en, this message translates to:
  /// **'Yours forever · no subscription'**
  String get chapterForeverNote;

  /// locked-chapter-spec §2 · C4 · бейдж живой системы в шапке главы (транзиты, соляр)
  ///
  /// In en, this message translates to:
  /// **'updates daily'**
  String get chapterDailyBadge;

  /// locked-chapter-spec §6 · C4 · строка «что дальше» у живой системы. Слово «навсегда» здесь запрещено
  ///
  /// In en, this message translates to:
  /// **'This one is rewritten every day — it lives in the subscription, not in a purchase'**
  String get chapterLivingNote;

  /// locked-chapter-spec §6 · строка «что дальше» над кнопкой: сколько глав этой системы ещё не написано
  ///
  /// In en, this message translates to:
  /// **'{n, plural, one{{n} chapter of your {system}, written from these positions} other{{n} chapters of your {system}, written from these positions}}'**
  String chapterWhatFollows(int n, String system);

  /// locked-chapter-spec §4 · C6 · природа покупки под кнопкой совместимости. Лимита на число людей нет и обещать его нельзя
  ///
  /// In en, this message translates to:
  /// **'Per person · yours forever · add as many as you like'**
  String get pairPerPersonNote;

  /// monetization v3 · W2 · подпись под заголовком анкеты пары
  ///
  /// In en, this message translates to:
  /// **'A date of birth is enough. A time makes the houses exact, but it can wait.'**
  String get pairInputNote;

  /// monetization v3 · А11 pair.input_time · W2
  ///
  /// In en, this message translates to:
  /// **'Time of birth'**
  String get pairInputTime;

  /// monetization v3 · А11 pair.input_optional · W2 — помета на поле времени
  ///
  /// In en, this message translates to:
  /// **'optional'**
  String get pairInputOptional;

  /// W2 · четвёртое поле, которого нет на холсте: сервер требует координаты и пояс (дома). Расхождение записано в SCREENS-V3 §W2 как вопрос владельцу
  ///
  /// In en, this message translates to:
  /// **'Place of birth'**
  String get pairInputPlace;

  /// monetization v3 · А11 pair.input_free_note · W2. Эталон холста написан про «его» карту; ключ родо-нейтрален — род партнёра здесь не спрашивают
  ///
  /// In en, this message translates to:
  /// **'Their chart is calculated for free, like yours. How the first chapter — attraction — begins, you read before deciding anything.'**
  String get pairInputFreeNote;

  /// monetization v3 · А11 pair.input_cta · W2
  ///
  /// In en, this message translates to:
  /// **'Read what pulls you together'**
  String get pairInputCta;

  /// monetization v3 · А11 pair.my_pairs_note · V5
  ///
  /// In en, this message translates to:
  /// **'Every report stays yours, subscription or not.'**
  String get pairMyPairsNote;

  /// monetization v3 · А11 pair.row_chapters · V5
  ///
  /// In en, this message translates to:
  /// **'four chapters'**
  String get pairRowChapters;

  /// monetization v3 · А11 pair.row_bought · V5
  ///
  /// In en, this message translates to:
  /// **'bought {date}'**
  String pairRowBought(String date);

  /// V5 · строка человека без купленного отчёта; кадра нет (SCREENS-V3 §V5), фраза собрана из pair.hook_note
  ///
  /// In en, this message translates to:
  /// **'how Attraction begins is free to read'**
  String get pairRowFreeChapter;

  /// monetization v3 · А11 pair.credit_overline · V5
  ///
  /// In en, this message translates to:
  /// **'this month'**
  String get pairCreditOverline;

  /// monetization v3 · А11 pair.credit_used · V5 — plural по обоим числам
  ///
  /// In en, this message translates to:
  /// **'{used} of {granted, plural, one{{granted} check used} other{{granted} checks used}}'**
  String pairCreditUsed(int used, int granted);

  /// monetization v3 · А11 pair.credit_next · V5
  ///
  /// In en, this message translates to:
  /// **'Your next included check arrives {date}. Checks do not carry over.'**
  String pairCreditNext(String date);

  /// monetization v3 · А11 pair.hook_title · V5
  ///
  /// In en, this message translates to:
  /// **'Anyone else on your mind?'**
  String get pairHookTitle;

  /// monetization v3 · А11 pair.hook_note · V5
  ///
  /// In en, this message translates to:
  /// **'A date of birth is enough — you read how Attraction begins before paying anything.'**
  String get pairHookNote;

  /// V5 · кнопка без цены: полка молчит или месячная проверка ещё не потрачена. Эталона на холсте нет (§V5, «кредит не потрачен»); это pair.check_another без цены
  ///
  /// In en, this message translates to:
  /// **'Check someone else'**
  String get pairCheckAnotherPlain;

  /// monetization v3 · А11 pair.report_header · W3 (и V4 до слияния тизера с главой I)
  ///
  /// In en, this message translates to:
  /// **'you and {name}'**
  String pairReportHeader(String name);

  /// monetization v3 · А11 pair.report_meta · W3 — только у купленного отчёта: подтверждение, а не оффер
  ///
  /// In en, this message translates to:
  /// **'four chapters · yours forever'**
  String get pairReportMeta;

  /// monetization v3 · А11 pair.chapter_read · W3 — метка прочитанной главы в оглавлении пары
  ///
  /// In en, this message translates to:
  /// **'read'**
  String get pairChapterRead;

  /// monetization v3 · home.living_layer · W4 — оверлайн раздела закрытых блоков на «Сегодня»
  ///
  /// In en, this message translates to:
  /// **'the living layer'**
  String get homeLivingLayer;

  /// monetization v3 · live.transits_title · W4
  ///
  /// In en, this message translates to:
  /// **'Transits of the week'**
  String get liveTransitsTitle;

  /// monetization v3 · live.transits_note · W4 — живое число из расчёта транзитов, не из словаря
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one{One exact aspect between now and Sunday} other{{count} exact aspects between now and Sunday}}'**
  String liveTransitsNote(int count);

  /// monetization v3 · W4 — тихая неделя или расчёт ещё не пришёл; на холсте не нарисовано, зеркалит cabAreaQuiet
  ///
  /// In en, this message translates to:
  /// **'Nothing exact before Sunday'**
  String get liveTransitsNoteQuiet;

  /// monetization v3 · live.solar_title · W4
  ///
  /// In en, this message translates to:
  /// **'Your solar year'**
  String get liveSolarTitle;

  /// monetization v3 · live.solar_note · W4
  ///
  /// In en, this message translates to:
  /// **'Rewritten every birthday, running now'**
  String get liveSolarNote;

  /// monetization v3 · live.day_title · W4
  ///
  /// In en, this message translates to:
  /// **'The day in full'**
  String get liveDayTitle;

  /// monetization v3 · live.day_note · W4
  ///
  /// In en, this message translates to:
  /// **'The long reading, areas, what is coming'**
  String get liveDayNote;

  /// monetization v3 · sub.badge · W5 — тихая метка в шапке панели гороскопа подписчика
  ///
  /// In en, this message translates to:
  /// **'subscribed'**
  String get paywallV3SubBadge;

  /// monetization v3 · sub.cancel_honesty · W5 — зачин до двоеточия красится goldBright; сокращать и разбивать нельзя (§7 ТЗ)
  ///
  /// In en, this message translates to:
  /// **'If you ever cancel: chapters bought as a door stay readable. Chapters open only through the subscription close with it — the calculation stays free either way.'**
  String get paywallV3SubCancelHonesty;

  /// monetization v3 · state.processing_note · W6
  ///
  /// In en, this message translates to:
  /// **'Apple has taken it; we are writing it down. This finishes by itself, even if you close the app.'**
  String get paywallV3StateProcessingNote;

  /// onboarding · coach.systems.title — первый шаг обучалки, заголовок карточки
  ///
  /// In en, this message translates to:
  /// **'Your eight systems'**
  String get onbSystemsTitle;

  /// onboarding · coach.systems.body — восемь систем по рождению; расчёт бесплатен всегда, платны написанные главы, первая глава натала открыта
  ///
  /// In en, this message translates to:
  /// **'All eight are calculated from your birth, and the calculation stays free — always. Only the written chapters are paid, and the first chapter of your natal chart is already open.'**
  String get onbSystemsBody;

  /// onboarding · coach.today.title — второй шаг обучалки, заголовок карточки
  ///
  /// In en, this message translates to:
  /// **'A page for every day'**
  String get onbTodayTitle;

  /// onboarding · coach.today.body — заметка дня из собственной карты, живой слой пересчитывается вместе с небом
  ///
  /// In en, this message translates to:
  /// **'The note of the day is written from your own chart. The living layer — transits, solar return, compatibility — is recalculated together with the sky.'**
  String get onbTodayBody;

  /// onboarding · coach.next — кнопка перехода к следующему шагу
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get onbNext;

  /// onboarding · coach.done — кнопка последнего шага; закрывает обучалку
  ///
  /// In en, this message translates to:
  /// **'Got it'**
  String get onbDone;

  /// onboarding · coach.close — подпись крестика для озвучки экрана
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get onbClose;
}

class _LDelegate extends LocalizationsDelegate<L> {
  const _LDelegate();

  @override
  Future<L> load(Locale locale) {
    return SynchronousFuture<L>(lookupL(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>[
    'de',
    'en',
    'es',
    'fr',
    'it',
    'pt',
    'ru',
  ].contains(locale.languageCode);

  @override
  bool shouldReload(_LDelegate old) => false;
}

L lookupL(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return LDe();
    case 'en':
      return LEn();
    case 'es':
      return LEs();
    case 'fr':
      return LFr();
    case 'it':
      return LIt();
    case 'pt':
      return LPt();
    case 'ru':
      return LRu();
  }

  throw FlutterError(
    'L.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
