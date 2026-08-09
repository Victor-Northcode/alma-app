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

  /// from Cabinet/cab.acrossSystems
  ///
  /// In en, this message translates to:
  /// **'across your systems'**
  String get cabAcrossSystems;

  /// from Cabinet/cab.activeNow
  ///
  /// In en, this message translates to:
  /// **'active now'**
  String get cabActiveNow;

  /// from Cabinet/cab.addAPerson
  ///
  /// In en, this message translates to:
  /// **'Add a person'**
  String get cabAddAPerson;

  /// from Cabinet/cab.addBirthData
  ///
  /// In en, this message translates to:
  /// **'Enter my birth data'**
  String get cabAddBirthData;

  /// from Cabinet/cab.addBirthTime
  ///
  /// In en, this message translates to:
  /// **'Add my birth time'**
  String get cabAddBirthTime;

  /// from Cabinet/cab.advice
  ///
  /// In en, this message translates to:
  /// **'what to do with it'**
  String get cabAdvice;

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

  /// from Cabinet/cab.archiveNote
  ///
  /// In en, this message translates to:
  /// **'All eight systems, bought once.'**
  String get cabArchiveNote;

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

  /// from Cabinet/cab.ascendant
  ///
  /// In en, this message translates to:
  /// **'Ascendant'**
  String get cabAscendant;

  /// from Cabinet/cab.askAlma
  ///
  /// In en, this message translates to:
  /// **'Ask Alma a question'**
  String get cabAskAlma;

  /// from Cabinet/cab.aspect.meaning.conjunction
  ///
  /// In en, this message translates to:
  /// **'In the same place: they work as one thing and amplify each other.'**
  String get cabAspectMeaningConjunction;

  /// from Cabinet/cab.aspect.meaning.opposition
  ///
  /// In en, this message translates to:
  /// **'Facing each other: they pull opposite ways, and you choose every time.'**
  String get cabAspectMeaningOpposition;

  /// from Cabinet/cab.aspect.meaning.quincunx
  ///
  /// In en, this message translates to:
  /// **'They cannot see each other: two demands that do not reconcile.'**
  String get cabAspectMeaningQuincunx;

  /// from Cabinet/cab.aspect.meaning.sextile
  ///
  /// In en, this message translates to:
  /// **'They help each other, if you put the effort in.'**
  String get cabAspectMeaningSextile;

  /// from Cabinet/cab.aspect.meaning.square
  ///
  /// In en, this message translates to:
  /// **'They get in each other\'s way: the place where you have to cope.'**
  String get cabAspectMeaningSquare;

  /// from Cabinet/cab.aspect.meaning.trine
  ///
  /// In en, this message translates to:
  /// **'They fit together easily — so easily that it is rarely used on purpose.'**
  String get cabAspectMeaningTrine;

  /// from Cabinet/cab.axis.Character
  ///
  /// In en, this message translates to:
  /// **'Character'**
  String get cabAxisCharacter;

  /// from Cabinet/cab.axis.Direction
  ///
  /// In en, this message translates to:
  /// **'Direction'**
  String get cabAxisDirection;

  /// from Cabinet/cab.axis.Growth
  ///
  /// In en, this message translates to:
  /// **'Growth'**
  String get cabAxisGrowth;

  /// from Cabinet/cab.axis.Mind
  ///
  /// In en, this message translates to:
  /// **'Mind'**
  String get cabAxisMind;

  /// from Cabinet/cab.axis.Relationships
  ///
  /// In en, this message translates to:
  /// **'Relationships'**
  String get cabAxisRelationships;

  /// from Cabinet/cab.axis.Resources
  ///
  /// In en, this message translates to:
  /// **'Resources'**
  String get cabAxisResources;

  /// from Cabinet/cab.axis.Rhythms
  ///
  /// In en, this message translates to:
  /// **'Rhythms'**
  String get cabAxisRhythms;

  /// from Cabinet/cab.axis.Weak-point
  ///
  /// In en, this message translates to:
  /// **'Weak point'**
  String get cabAxisWeakPoint;

  /// from Cabinet/cab.axis.Work
  ///
  /// In en, this message translates to:
  /// **'Work'**
  String get cabAxisWork;

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

  /// from Cabinet/cab.chapterEnd.door
  ///
  /// In en, this message translates to:
  /// **'The rest of this system is written the same way — from your positions, yours to keep.'**
  String get cabChapterEndDoor;

  /// from Cabinet/cab.chapterEnd.plan
  ///
  /// In en, this message translates to:
  /// **'This chapter is written once. Transits, the year and compatibility are rewritten as the sky moves — that is the plan.'**
  String get cabChapterEndPlan;

  /// from Cabinet/cab.chapterProgress
  ///
  /// In en, this message translates to:
  /// **'{p1} of {p2}'**
  String cabChapterProgress(int p1, int p2);

  /// from Cabinet/cab.chapters
  ///
  /// In en, this message translates to:
  /// **'chapters'**
  String get cabChapters;

  /// from Cabinet/cab.compatNeedsPerson
  ///
  /// In en, this message translates to:
  /// **'Compatibility needs a second birth. Add somebody and the whole comparison is calculated free.'**
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

  /// from Cabinet/cab.fact.birthdayNumber
  ///
  /// In en, this message translates to:
  /// **'birthday number'**
  String get cabFactBirthdayNumber;

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

  /// from Cabinet/cab.fact.destinyNumber
  ///
  /// In en, this message translates to:
  /// **'destiny number'**
  String get cabFactDestinyNumber;

  /// from Cabinet/cab.fact.element
  ///
  /// In en, this message translates to:
  /// **'element'**
  String get cabFactElement;

  /// from Cabinet/cab.fact.karmicDebt
  ///
  /// In en, this message translates to:
  /// **'karmic debt'**
  String get cabFactKarmicDebt;

  /// from Cabinet/cab.fact.lifePath
  ///
  /// In en, this message translates to:
  /// **'life path'**
  String get cabFactLifePath;

  /// from Cabinet/cab.fact.lines
  ///
  /// In en, this message translates to:
  /// **'lines'**
  String get cabFactLines;

  /// from Cabinet/cab.fact.personalityCard
  ///
  /// In en, this message translates to:
  /// **'personality card'**
  String get cabFactPersonalityCard;

  /// from Cabinet/cab.fact.return
  ///
  /// In en, this message translates to:
  /// **'return'**
  String get cabFactReturn;

  /// from Cabinet/cab.fact.ruler
  ///
  /// In en, this message translates to:
  /// **'ruler'**
  String get cabFactRuler;

  /// from Cabinet/cab.fact.year
  ///
  /// In en, this message translates to:
  /// **'year'**
  String get cabFactYear;

  /// from Cabinet/cab.fact.yearRuler
  ///
  /// In en, this message translates to:
  /// **'year ruler'**
  String get cabFactYearRuler;

  /// from Cabinet/cab.factor.acrossAxes
  ///
  /// In en, this message translates to:
  /// **'systems across nine axes'**
  String get cabFactorAcrossAxes;

  /// from Cabinet/cab.factor.agree
  ///
  /// In en, this message translates to:
  /// **'agree'**
  String get cabFactorAgree;

  /// from Cabinet/cab.factor.disagree
  ///
  /// In en, this message translates to:
  /// **'disagree'**
  String get cabFactorDisagree;

  /// from Cabinet/cab.factor.seenByOne
  ///
  /// In en, this message translates to:
  /// **'seen by one'**
  String get cabFactorSeenByOne;

  /// from Cabinet/cab.freeChapterNote
  ///
  /// In en, this message translates to:
  /// **'One chapter of every system is free.'**
  String get cabFreeChapterNote;

  /// from Cabinet/cab.freeTag
  ///
  /// In en, this message translates to:
  /// **'free'**
  String get cabFreeTag;

  /// from Cabinet/cab.fromYourPositions
  ///
  /// In en, this message translates to:
  /// **'Written from your own positions'**
  String get cabFromYourPositions;

  /// from Cabinet/cab.fullReading
  ///
  /// In en, this message translates to:
  /// **'Full reading'**
  String get cabFullReading;

  /// from Cabinet/cab.group.allOfIt
  ///
  /// In en, this message translates to:
  /// **'all of it'**
  String get cabGroupAllOfIt;

  /// from Cabinet/cab.group.howWeMatch
  ///
  /// In en, this message translates to:
  /// **'how we match'**
  String get cabGroupHowWeMatch;

  /// from Cabinet/cab.group.rightNow
  ///
  /// In en, this message translates to:
  /// **'right now'**
  String get cabGroupRightNow;

  /// from Cabinet/cab.group.thisYear
  ///
  /// In en, this message translates to:
  /// **'this year'**
  String get cabGroupThisYear;

  /// from Cabinet/cab.group.whereToBe
  ///
  /// In en, this message translates to:
  /// **'where to be'**
  String get cabGroupWhereToBe;

  /// from Cabinet/cab.group.whoAmI
  ///
  /// In en, this message translates to:
  /// **'who am I'**
  String get cabGroupWhoAmI;

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

  /// from Cabinet/cab.holdToTurn
  ///
  /// In en, this message translates to:
  /// **'Hold to open it'**
  String get cabHoldToTurn;

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

  /// from Cabinet/cab.languageNote
  ///
  /// In en, this message translates to:
  /// **'I read and write in the language of your phone. Change it there and I change with it.'**
  String get cabLanguageNote;

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

  /// from Cabinet/cab.lockedNote
  ///
  /// In en, this message translates to:
  /// **'Written from your own positions the first time you open it — your chart, never a template.'**
  String get cabLockedNote;

  /// from Cabinet/cab.lunarDay
  ///
  /// In en, this message translates to:
  /// **'Lunar day'**
  String get cabLunarDay;

  /// from Cabinet/cab.manageInStore
  ///
  /// In en, this message translates to:
  /// **'Manage this subscription in the App Store'**
  String get cabManageInStore;

  /// from Cabinet/cab.managedByApple
  ///
  /// In en, this message translates to:
  /// **'This plan was bought in the App Store, so Apple holds the payment method and the cancellation happens there.'**
  String get cabManagedByApple;

  /// from Cabinet/cab.merchantLine
  ///
  /// In en, this message translates to:
  /// **'Payments processed by {p1} as merchant of record · VAT/GST included where applicable'**
  String cabMerchantLine(String p1);

  /// from Cabinet/cab.needsBirthTime
  ///
  /// In en, this message translates to:
  /// **'This one needs your birth time.'**
  String get cabNeedsBirthTime;

  /// from Cabinet/cab.nextChapter
  ///
  /// In en, this message translates to:
  /// **'next'**
  String get cabNextChapter;

  /// from Cabinet/cab.noBirthData
  ///
  /// In en, this message translates to:
  /// **'Add your birth date and I can read you.'**
  String get cabNoBirthData;

  /// from Cabinet/cab.noneActive
  ///
  /// In en, this message translates to:
  /// **'Nothing is in orb today. That is an answer, not an empty screen.'**
  String get cabNoneActive;

  /// from Cabinet/cab.notCalculated
  ///
  /// In en, this message translates to:
  /// **'not calculated'**
  String get cabNotCalculated;

  /// from Cabinet/cab.notPrediction
  ///
  /// In en, this message translates to:
  /// **'Nothing here is a prediction. Every line names the placement it was read from.'**
  String get cabNotPrediction;

  /// from Cabinet/cab.oneTimeNote
  ///
  /// In en, this message translates to:
  /// **'One payment.'**
  String get cabOneTimeNote;

  /// from Cabinet/cab.openSystemNamed
  ///
  /// In en, this message translates to:
  /// **'Open {p1}'**
  String cabOpenSystemNamed(String p1);

  /// from Cabinet/cab.openTag
  ///
  /// In en, this message translates to:
  /// **'open'**
  String get cabOpenTag;

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

  /// from Cabinet/cab.placementsLabel
  ///
  /// In en, this message translates to:
  /// **'your placements'**
  String get cabPlacementsLabel;

  /// from Cabinet/cab.plan.annualPlan
  ///
  /// In en, this message translates to:
  /// **'Everything, for a year'**
  String get cabPlanAnnualPlan;

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

  /// from Cabinet/cab.plan.exportSaved
  ///
  /// In en, this message translates to:
  /// **'Saved as alma-export.json.'**
  String get cabPlanExportSaved;

  /// from Cabinet/cab.plan.exporting
  ///
  /// In en, this message translates to:
  /// **'Preparing your file…'**
  String get cabPlanExporting;

  /// from Cabinet/cab.plan.freeNote
  ///
  /// In en, this message translates to:
  /// **'Every calculation is free. You pay for the words, one reading at a time.'**
  String get cabPlanFreeNote;

  /// from Cabinet/cab.plan.freePlan
  ///
  /// In en, this message translates to:
  /// **'Free'**
  String get cabPlanFreePlan;

  /// from Cabinet/cab.plan.guestNote
  ///
  /// In en, this message translates to:
  /// **'You are not signed in. Your chart lives in this browser only.'**
  String get cabPlanGuestNote;

  /// from Cabinet/cab.plan.keepAccount
  ///
  /// In en, this message translates to:
  /// **'Keep my account'**
  String get cabPlanKeepAccount;

  /// from Cabinet/cab.plan.keepPlan
  ///
  /// In en, this message translates to:
  /// **'Keep my plan'**
  String get cabPlanKeepPlan;

  /// from Cabinet/cab.plan.needsAccount
  ///
  /// In en, this message translates to:
  /// **'This needs an account we can attach to you.'**
  String get cabPlanNeedsAccount;

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
  /// **'The plan keeps all eight systems open, sends the morning notification, rewrites your day as the sky moves — and Alma answers your questions in her deeper voice. Monthly or yearly.'**
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

  /// from Cabinet/cab.previewNote
  ///
  /// In en, this message translates to:
  /// **'The chapter is written. The rest opens with the system.'**
  String get cabPreviewNote;

  /// from Cabinet/cab.pullToTurn
  ///
  /// In en, this message translates to:
  /// **'Keep pulling to open it'**
  String get cabPullToTurn;

  /// from Cabinet/cab.questionsLeft
  ///
  /// In en, this message translates to:
  /// **'Questions left today: {p1}'**
  String cabQuestionsLeft(int p1);

  /// from Cabinet/cab.readFrom
  ///
  /// In en, this message translates to:
  /// **'read from'**
  String get cabReadFrom;

  /// from Cabinet/cab.readWholeDay
  ///
  /// In en, this message translates to:
  /// **'Read the whole day'**
  String get cabReadWholeDay;

  /// from Cabinet/cab.readingChart
  ///
  /// In en, this message translates to:
  /// **'Reading your chart'**
  String get cabReadingChart;

  /// from Cabinet/cab.rebuilds
  ///
  /// In en, this message translates to:
  /// **'Rebuilds itself when a system is added'**
  String get cabRebuilds;

  /// from Cabinet/cab.refused
  ///
  /// In en, this message translates to:
  /// **'I could not write this from your chart, so I did not.'**
  String get cabRefused;

  /// from Cabinet/cab.saveFile
  ///
  /// In en, this message translates to:
  /// **'Save the file'**
  String get cabSaveFile;

  /// from Cabinet/cab.score.attraction
  ///
  /// In en, this message translates to:
  /// **'attraction'**
  String get cabScoreAttraction;

  /// from Cabinet/cab.score.endurance
  ///
  /// In en, this message translates to:
  /// **'endurance'**
  String get cabScoreEndurance;

  /// from Cabinet/cab.score.friction
  ///
  /// In en, this message translates to:
  /// **'friction'**
  String get cabScoreFriction;

  /// from Cabinet/cab.score.warmth
  ///
  /// In en, this message translates to:
  /// **'warmth'**
  String get cabScoreWarmth;

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

  /// from Cabinet/cab.settings.letters
  ///
  /// In en, this message translates to:
  /// **'Letters'**
  String get cabSettingsLetters;

  /// from Cabinet/cab.settings.lettersNote
  ///
  /// In en, this message translates to:
  /// **'Alma sends three: your sign-in link, a receipt for anything you buy, and a warning three days before a plan renews. All three are about something you did. There is no newsletter and nothing to unsubscribe from.'**
  String get cabSettingsLettersNote;

  /// from Cabinet/cab.settings.lettersNoteStore
  ///
  /// In en, this message translates to:
  /// **'Alma sends one: your sign-in link. Apple sends the receipt for anything you buy in the app and the warning before a plan renews, because Apple takes the payment. There is no newsletter and nothing to unsubscribe from.'**
  String get cabSettingsLettersNoteStore;

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

  /// from Cabinet/cab.settings.privacy
  ///
  /// In en, this message translates to:
  /// **'Your privacy choices'**
  String get cabSettingsPrivacy;

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

  /// from Cabinet/cab.skyBehind
  ///
  /// In en, this message translates to:
  /// **'The sky behind it'**
  String get cabSkyBehind;

  /// from Cabinet/cab.skyEvent.body
  ///
  /// In en, this message translates to:
  /// **'Days like this are what the morning notification is for — it arrives at 08:00 when something in your chart is exact. Part of the plan.'**
  String get cabSkyEventBody;

  /// from Cabinet/cab.spheresLabel
  ///
  /// In en, this message translates to:
  /// **'what the chart says'**
  String get cabSpheresLabel;

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

  /// from Cabinet/cab.strongestAspects
  ///
  /// In en, this message translates to:
  /// **'what agrees and what argues'**
  String get cabStrongestAspects;

  /// from Cabinet/cab.sunInSign
  ///
  /// In en, this message translates to:
  /// **'Sun in {p1}'**
  String cabSunInSign(String p1);

  /// from Cabinet/cab.synth.lead
  ///
  /// In en, this message translates to:
  /// **'Three agreeing is the closest thing to proof. Two disagreeing is more useful still — that\'s the conflict you keep living out.'**
  String get cabSynthLead;

  /// from Cabinet/cab.synth.single
  ///
  /// In en, this message translates to:
  /// **'seen by one'**
  String get cabSynthSingle;

  /// from Cabinet/cab.synth.title
  ///
  /// In en, this message translates to:
  /// **'Where three systems agree about you'**
  String get cabSynthTitle;

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

  /// from Cabinet/cab.systemFinished
  ///
  /// In en, this message translates to:
  /// **'You have read all of this one'**
  String get cabSystemFinished;

  /// from Cabinet/cab.unknownTime
  ///
  /// In en, this message translates to:
  /// **'birth time unknown'**
  String get cabUnknownTime;

  /// from Cabinet/cab.unlock
  ///
  /// In en, this message translates to:
  /// **'Unlock'**
  String get cabUnlock;

  /// from Cabinet/cab.upcoming
  ///
  /// In en, this message translates to:
  /// **'coming up'**
  String get cabUpcoming;

  /// from Cabinet/cab.writingNote
  ///
  /// In en, this message translates to:
  /// **'It is written once, and it will say the same thing tomorrow.'**
  String get cabWritingNote;

  /// from Cabinet/cab.yourDay
  ///
  /// In en, this message translates to:
  /// **'Your day'**
  String get cabYourDay;

  /// from Daily/daily.action.quieter
  ///
  /// In en, this message translates to:
  /// **'Fewer of these'**
  String get dailyActionQuieter;

  /// from Daily/daily.action.turnOff
  ///
  /// In en, this message translates to:
  /// **'Turn these off'**
  String get dailyActionTurnOff;

  /// from Daily/daily.action.turnedOff
  ///
  /// In en, this message translates to:
  /// **'Turned off. Today is still here whenever you open it.'**
  String get dailyActionTurnedOff;

  /// from Daily/daily.ask.body
  ///
  /// In en, this message translates to:
  /// **'One notification, at the hour you choose, on the days something in your chart is exact. About once a week. Never at night, and it can be turned off from the notification itself.'**
  String get dailyAskBody;

  /// from Daily/daily.ask.no
  ///
  /// In en, this message translates to:
  /// **'Not now'**
  String get dailyAskNo;

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

  /// from Daily/daily.empty.body
  ///
  /// In en, this message translates to:
  /// **'What is still in orb is below. Nothing perfects today.'**
  String get dailyEmptyBody;

  /// from Daily/daily.empty.title
  ///
  /// In en, this message translates to:
  /// **'Nothing is exact today'**
  String get dailyEmptyTitle;

  /// from Daily/daily.retrograde
  ///
  /// In en, this message translates to:
  /// **'retrograde'**
  String get dailyRetrograde;

  /// from Daily/daily.running.body
  ///
  /// In en, this message translates to:
  /// **'The closest is {p1}. Everything else is moving slowly.'**
  String dailyRunningBody(String p1);

  /// from Daily/daily.running.nearest
  ///
  /// In en, this message translates to:
  /// **'The closest is {p1}, exact on {p2}. Everything else is moving slowly.'**
  String dailyRunningNearest(String p1, String p2);

  /// from Daily/daily.running.title
  ///
  /// In en, this message translates to:
  /// **'Nothing exact today'**
  String get dailyRunningTitle;

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

  /// from Daily/daily.setting.off.detail
  ///
  /// In en, this message translates to:
  /// **'No notifications. Today is still here whenever you open it.'**
  String get dailySettingOffDetail;

  /// from Daily/daily.setting.onlyMatters.detail
  ///
  /// In en, this message translates to:
  /// **'A few times a year. The slow ones only — the transits that last months.'**
  String get dailySettingOnlyMattersDetail;

  /// from Daily/daily.setting.onlyWhatMatters
  ///
  /// In en, this message translates to:
  /// **'Only what matters'**
  String get dailySettingOnlyWhatMatters;

  /// from Daily/daily.setting.quiet
  ///
  /// In en, this message translates to:
  /// **'Never between 22:00 and 08:00, in your time.'**
  String get dailySettingQuiet;

  /// from Daily/daily.setting.timezone
  ///
  /// In en, this message translates to:
  /// **'Your time'**
  String get dailySettingTimezone;

  /// from Daily/daily.setting.timezone.birth
  ///
  /// In en, this message translates to:
  /// **'from your birth data'**
  String get dailySettingTimezoneBirth;

  /// from Daily/daily.setting.timezone.chosen
  ///
  /// In en, this message translates to:
  /// **'you chose this'**
  String get dailySettingTimezoneChosen;

  /// from Daily/daily.setting.timezone.device
  ///
  /// In en, this message translates to:
  /// **'from your device'**
  String get dailySettingTimezoneDevice;

  /// from Daily/daily.setting.title
  ///
  /// In en, this message translates to:
  /// **'The daily'**
  String get dailySettingTitle;

  /// from Daily/daily.status.denied
  ///
  /// In en, this message translates to:
  /// **'Notifications are off for Alma. You can turn them on in your phone\'s settings.'**
  String get dailyStatusDenied;

  /// from Daily/daily.status.notDelivering
  ///
  /// In en, this message translates to:
  /// **'Nothing is being sent yet. This phone is not registered for notifications, so the daily lives here, on Today.'**
  String get dailyStatusNotDelivering;

  /// from Daily/daily.status.openSettings
  ///
  /// In en, this message translates to:
  /// **'Open settings'**
  String get dailyStatusOpenSettings;

  /// from Daily/daily.status.provisional
  ///
  /// In en, this message translates to:
  /// **'Arriving quietly. Alma\'s notifications go straight to Notification Center — no banner, no sound — until you decide otherwise.'**
  String get dailyStatusProvisional;

  /// from Daily/daily.status.registered
  ///
  /// In en, this message translates to:
  /// **'This phone is registered for the daily.'**
  String get dailyStatusRegistered;

  /// from Daily/daily.status.upgrade
  ///
  /// In en, this message translates to:
  /// **'Let them arrive properly'**
  String get dailyStatusUpgrade;

  /// from Daily/daily.subscriberOnly
  ///
  /// In en, this message translates to:
  /// **'The morning notification is part of the plan.'**
  String get dailySubscriberOnly;

  /// from Daily/daily.today.at
  ///
  /// In en, this message translates to:
  /// **'Exact at {p1}'**
  String dailyTodayAt(String p1);

  /// from Daily/daily.today.label
  ///
  /// In en, this message translates to:
  /// **'Exact today'**
  String get dailyTodayLabel;

  /// from Daily/daily.today.since
  ///
  /// In en, this message translates to:
  /// **'In orb since {p1}'**
  String dailyTodaySince(String p1);

  /// from Daily/daily.today.until
  ///
  /// In en, this message translates to:
  /// **'in orb until {p1}'**
  String dailyTodayUntil(String p1);

  /// from Daily/daily.verified.label
  ///
  /// In en, this message translates to:
  /// **'Exact days in the next 30'**
  String get dailyVerifiedLabel;

  /// from Daily/daily.verified.note
  ///
  /// In en, this message translates to:
  /// **'Counted from your own chart, on this device, with the same rule the notification uses.'**
  String get dailyVerifiedNote;

  /// from Daily/daily.your
  ///
  /// In en, this message translates to:
  /// **'your'**
  String get dailyYour;

  /// from Journey/journey.aboutSub
  ///
  /// In en, this message translates to:
  /// **'You can skip this.'**
  String get journeyAboutSub;

  /// from Journey/journey.aboutTitle
  ///
  /// In en, this message translates to:
  /// **'A little about you'**
  String get journeyAboutTitle;

  /// from Journey/journey.ascendant
  ///
  /// In en, this message translates to:
  /// **'Ascendant'**
  String get journeyAscendant;

  /// from Journey/journey.back
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get journeyBack;

  /// from Journey/journey.buildMySky
  ///
  /// In en, this message translates to:
  /// **'Build my sky'**
  String get journeyBuildMySky;

  /// from Journey/journey.calculated
  ///
  /// In en, this message translates to:
  /// **'all eight systems · calculated'**
  String get journeyCalculated;

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

  /// from Journey/journey.capture.noPlaces
  ///
  /// In en, this message translates to:
  /// **'No place by that name. Try the nearest larger town.'**
  String get journeyCaptureNoPlaces;

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
  /// **'Ten planets, twelve houses — your chart is drawn from real ephemeris data.'**
  String get journeyCeremony1Line;

  /// from Journey/journey.ceremony.2.label
  ///
  /// In en, this message translates to:
  /// **'reading system 2 of 8 · numerology'**
  String get journeyCeremony2Label;

  /// from Journey/journey.ceremony.2.line
  ///
  /// In en, this message translates to:
  /// **'Your life path reduces to a number that prefers proof over belief.'**
  String get journeyCeremony2Line;

  /// from Journey/journey.ceremony.3.label
  ///
  /// In en, this message translates to:
  /// **'reading system 3 of 8 · birth card'**
  String get journeyCeremony3Label;

  /// from Journey/journey.ceremony.3.line
  ///
  /// In en, this message translates to:
  /// **'One of twenty-two arcana, calculated from the date alone.'**
  String get journeyCeremony3Line;

  /// from Journey/journey.ceremony.4.label
  ///
  /// In en, this message translates to:
  /// **'reading system 4 of 8 · transits'**
  String get journeyCeremony4Label;

  /// from Journey/journey.ceremony.4.line
  ///
  /// In en, this message translates to:
  /// **'Where the sky is now, against where it was when you started.'**
  String get journeyCeremony4Line;

  /// from Journey/journey.ceremony.5.label
  ///
  /// In en, this message translates to:
  /// **'reading system 5 of 8 · compatibility'**
  String get journeyCeremony5Label;

  /// from Journey/journey.ceremony.5.line
  ///
  /// In en, this message translates to:
  /// **'Held open until you add a second person — nothing invented.'**
  String get journeyCeremony5Line;

  /// from Journey/journey.ceremony.6.label
  ///
  /// In en, this message translates to:
  /// **'reading system 6 of 8 · solar return'**
  String get journeyCeremony6Label;

  /// from Journey/journey.ceremony.6.line
  ///
  /// In en, this message translates to:
  /// **'The year ahead, read from the minute the Sun comes back to its place.'**
  String get journeyCeremony6Line;

  /// from Journey/journey.ceremony.7.label
  ///
  /// In en, this message translates to:
  /// **'reading system 7 of 8 · astrocartography'**
  String get journeyCeremony7Label;

  /// from Journey/journey.ceremony.7.line
  ///
  /// In en, this message translates to:
  /// **'Planetary lines across the map, drawn from your exact minute.'**
  String get journeyCeremony7Line;

  /// from Journey/journey.ceremony.8.label
  ///
  /// In en, this message translates to:
  /// **'reading system 8 of 8 · cross-synthesis'**
  String get journeyCeremony8Label;

  /// from Journey/journey.ceremony.8.line
  ///
  /// In en, this message translates to:
  /// **'Nine axes. Where three traditions agree, that goes to your core.'**
  String get journeyCeremony8Line;

  /// from Journey/journey.ceremonySkip
  ///
  /// In en, this message translates to:
  /// **'Skip the ceremony'**
  String get journeyCeremonySkip;

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

  /// from Journey/journey.dialogLabel
  ///
  /// In en, this message translates to:
  /// **'Getting to know you'**
  String get journeyDialogLabel;

  /// from Journey/journey.freeChapterLabel
  ///
  /// In en, this message translates to:
  /// **'your first chapter · free'**
  String get journeyFreeChapterLabel;

  /// from Journey/journey.freeLabel
  ///
  /// In en, this message translates to:
  /// **'yours, free, forever'**
  String get journeyFreeLabel;

  /// from Journey/journey.freeNote
  ///
  /// In en, this message translates to:
  /// **'These two systems never cost anything. They are yours whether you read further or not.'**
  String get journeyFreeNote;

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

  /// from Journey/journey.handoffSub
  ///
  /// In en, this message translates to:
  /// **'Three rules that make this work — the only onboarding we\'ll ever give you.'**
  String get journeyHandoffSub;

  /// from Journey/journey.handoffTitle
  ///
  /// In en, this message translates to:
  /// **'Saved. Now read yourself slowly.'**
  String get journeyHandoffTitle;

  /// from Journey/journey.hourLabel
  ///
  /// In en, this message translates to:
  /// **'Hour'**
  String get journeyHourLabel;

  /// from Journey/journey.insight.lifePath
  ///
  /// In en, this message translates to:
  /// **'Life path {p1}'**
  String journeyInsightLifePath(String p1);

  /// from Journey/journey.insight.sun
  ///
  /// In en, this message translates to:
  /// **'Sun in {p1}'**
  String journeyInsightSun(String p1);

  /// from Journey/journey.intent.self
  ///
  /// In en, this message translates to:
  /// **'Who am I, really'**
  String get journeyIntentSelf;

  /// from Journey/journey.intent.shifting
  ///
  /// In en, this message translates to:
  /// **'Something\'s shifting and I don\'t know why'**
  String get journeyIntentShifting;

  /// from Journey/journey.intent.us
  ///
  /// In en, this message translates to:
  /// **'Us — will this work'**
  String get journeyIntentUs;

  /// from Journey/journey.intent.where
  ///
  /// In en, this message translates to:
  /// **'Where I should live'**
  String get journeyIntentWhere;

  /// from Journey/journey.intentSkip
  ///
  /// In en, this message translates to:
  /// **'Skip — I know what I want'**
  String get journeyIntentSkip;

  /// from Journey/journey.intentTitle
  ///
  /// In en, this message translates to:
  /// **'What\'s loudest in you right now?'**
  String get journeyIntentTitle;

  /// from Journey/journey.keepMySky
  ///
  /// In en, this message translates to:
  /// **'Keep my sky'**
  String get journeyKeepMySky;

  /// from Journey/journey.lockedWithoutTime
  ///
  /// In en, this message translates to:
  /// **'Houses, solar return and map stay locked'**
  String get journeyLockedWithoutTime;

  /// from Journey/journey.meridiemLabel
  ///
  /// In en, this message translates to:
  /// **'AM or PM'**
  String get journeyMeridiemLabel;

  /// from Journey/journey.minuteLabel
  ///
  /// In en, this message translates to:
  /// **'Min'**
  String get journeyMinuteLabel;

  /// from Journey/journey.month.1
  ///
  /// In en, this message translates to:
  /// **'January'**
  String get journeyMonth1;

  /// from Journey/journey.month.10
  ///
  /// In en, this message translates to:
  /// **'October'**
  String get journeyMonth10;

  /// from Journey/journey.month.11
  ///
  /// In en, this message translates to:
  /// **'November'**
  String get journeyMonth11;

  /// from Journey/journey.month.12
  ///
  /// In en, this message translates to:
  /// **'December'**
  String get journeyMonth12;

  /// from Journey/journey.month.2
  ///
  /// In en, this message translates to:
  /// **'February'**
  String get journeyMonth2;

  /// from Journey/journey.month.3
  ///
  /// In en, this message translates to:
  /// **'March'**
  String get journeyMonth3;

  /// from Journey/journey.month.4
  ///
  /// In en, this message translates to:
  /// **'April'**
  String get journeyMonth4;

  /// from Journey/journey.month.5
  ///
  /// In en, this message translates to:
  /// **'May'**
  String get journeyMonth5;

  /// from Journey/journey.month.6
  ///
  /// In en, this message translates to:
  /// **'June'**
  String get journeyMonth6;

  /// from Journey/journey.month.7
  ///
  /// In en, this message translates to:
  /// **'July'**
  String get journeyMonth7;

  /// from Journey/journey.month.8
  ///
  /// In en, this message translates to:
  /// **'August'**
  String get journeyMonth8;

  /// from Journey/journey.month.9
  ///
  /// In en, this message translates to:
  /// **'September'**
  String get journeyMonth9;

  /// from Journey/journey.moon
  ///
  /// In en, this message translates to:
  /// **'Moon'**
  String get journeyMoon;

  /// from Journey/journey.nameAria
  ///
  /// In en, this message translates to:
  /// **'Your name'**
  String get journeyNameAria;

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

  /// from Journey/journey.needsTime
  ///
  /// In en, this message translates to:
  /// **'needs birth time'**
  String get journeyNeedsTime;

  /// from Journey/journey.needsTimeRow
  ///
  /// In en, this message translates to:
  /// **'Solar return · map'**
  String get journeyNeedsTimeRow;

  /// from Journey/journey.offerCta
  ///
  /// In en, this message translates to:
  /// **'Read it'**
  String get journeyOfferCta;

  /// from Journey/journey.offerFine
  ///
  /// In en, this message translates to:
  /// **'One payment. Yours permanently. No account needed to buy.'**
  String get journeyOfferFine;

  /// from Journey/journey.offerSkip
  ///
  /// In en, this message translates to:
  /// **'Not now — take me in'**
  String get journeyOfferSkip;

  /// from Journey/journey.offerSub
  ///
  /// In en, this message translates to:
  /// **'The numbers above are yours and stay free. This opens the whole system — every chapter of the reading, written from your positions, not a template.'**
  String get journeyOfferSub;

  /// from Journey/journey.offerTitle
  ///
  /// In en, this message translates to:
  /// **'Your {p1}, written'**
  String journeyOfferTitle(String p1);

  /// from Journey/journey.openToday
  ///
  /// In en, this message translates to:
  /// **'Open my Today'**
  String get journeyOpenToday;

  /// from Journey/journey.phase.firstQuarter
  ///
  /// In en, this message translates to:
  /// **'first quarter'**
  String get journeyPhaseFirstQuarter;

  /// from Journey/journey.phase.fullMoon
  ///
  /// In en, this message translates to:
  /// **'full moon'**
  String get journeyPhaseFullMoon;

  /// from Journey/journey.phase.lastQuarter
  ///
  /// In en, this message translates to:
  /// **'last quarter'**
  String get journeyPhaseLastQuarter;

  /// from Journey/journey.phase.newMoon
  ///
  /// In en, this message translates to:
  /// **'new moon'**
  String get journeyPhaseNewMoon;

  /// from Journey/journey.phase.waningCrescent
  ///
  /// In en, this message translates to:
  /// **'waning crescent'**
  String get journeyPhaseWaningCrescent;

  /// from Journey/journey.phase.waningGibbous
  ///
  /// In en, this message translates to:
  /// **'waning gibbous'**
  String get journeyPhaseWaningGibbous;

  /// from Journey/journey.phase.waxingCrescent
  ///
  /// In en, this message translates to:
  /// **'waxing crescent'**
  String get journeyPhaseWaxingCrescent;

  /// from Journey/journey.phase.waxingGibbous
  ///
  /// In en, this message translates to:
  /// **'waxing gibbous'**
  String get journeyPhaseWaxingGibbous;

  /// from Journey/journey.placePlaceholder
  ///
  /// In en, this message translates to:
  /// **'City'**
  String get journeyPlacePlaceholder;

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

  /// from Journey/journey.rule.1
  ///
  /// In en, this message translates to:
  /// **'One chapter at a time. Sixteen at once is noise.'**
  String get journeyRule1;

  /// from Journey/journey.rule.2
  ///
  /// In en, this message translates to:
  /// **'When two systems disagree, don\'t pick a winner. That\'s the material.'**
  String get journeyRule2;

  /// from Journey/journey.rule.3
  ///
  /// In en, this message translates to:
  /// **'Ask me in your own words. Three questions are free.'**
  String get journeyRule3;

  /// from Journey/journey.sign.Aquarius
  ///
  /// In en, this message translates to:
  /// **'Aquarius'**
  String get journeySignAquarius;

  /// from Journey/journey.sign.Aries
  ///
  /// In en, this message translates to:
  /// **'Aries'**
  String get journeySignAries;

  /// from Journey/journey.sign.Cancer
  ///
  /// In en, this message translates to:
  /// **'Cancer'**
  String get journeySignCancer;

  /// from Journey/journey.sign.Capricorn
  ///
  /// In en, this message translates to:
  /// **'Capricorn'**
  String get journeySignCapricorn;

  /// from Journey/journey.sign.Gemini
  ///
  /// In en, this message translates to:
  /// **'Gemini'**
  String get journeySignGemini;

  /// from Journey/journey.sign.Leo
  ///
  /// In en, this message translates to:
  /// **'Leo'**
  String get journeySignLeo;

  /// from Journey/journey.sign.Libra
  ///
  /// In en, this message translates to:
  /// **'Libra'**
  String get journeySignLibra;

  /// from Journey/journey.sign.Pisces
  ///
  /// In en, this message translates to:
  /// **'Pisces'**
  String get journeySignPisces;

  /// from Journey/journey.sign.Sagittarius
  ///
  /// In en, this message translates to:
  /// **'Sagittarius'**
  String get journeySignSagittarius;

  /// from Journey/journey.sign.Scorpio
  ///
  /// In en, this message translates to:
  /// **'Scorpio'**
  String get journeySignScorpio;

  /// from Journey/journey.sign.Taurus
  ///
  /// In en, this message translates to:
  /// **'Taurus'**
  String get journeySignTaurus;

  /// from Journey/journey.sign.Virgo
  ///
  /// In en, this message translates to:
  /// **'Virgo'**
  String get journeySignVirgo;

  /// from Journey/journey.staysFree
  ///
  /// In en, this message translates to:
  /// **'Everything above stays free, forever'**
  String get journeyStaysFree;

  /// from Journey/journey.step
  ///
  /// In en, this message translates to:
  /// **'Step {p1} of {p2}'**
  String journeyStep(String p1, String p2);

  /// from Journey/journey.system.astrocartography
  ///
  /// In en, this message translates to:
  /// **'Astrocartography'**
  String get journeySystemAstrocartography;

  /// from Journey/journey.system.birth-card
  ///
  /// In en, this message translates to:
  /// **'Birth Card'**
  String get journeySystemBirthCard;

  /// from Journey/journey.system.compatibility
  ///
  /// In en, this message translates to:
  /// **'Compatibility'**
  String get journeySystemCompatibility;

  /// from Journey/journey.system.natal
  ///
  /// In en, this message translates to:
  /// **'Natal chart'**
  String get journeySystemNatal;

  /// from Journey/journey.system.numerology
  ///
  /// In en, this message translates to:
  /// **'Numerology'**
  String get journeySystemNumerology;

  /// from Journey/journey.system.solar-return
  ///
  /// In en, this message translates to:
  /// **'Solar return'**
  String get journeySystemSolarReturn;

  /// from Journey/journey.system.synthesis
  ///
  /// In en, this message translates to:
  /// **'Cross-synthesis'**
  String get journeySystemSynthesis;

  /// from Journey/journey.system.transits
  ///
  /// In en, this message translates to:
  /// **'Transits'**
  String get journeySystemTransits;

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

  /// from Localizable/cabinet.sections
  ///
  /// In en, this message translates to:
  /// **'Sections'**
  String get cabinetSections;

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

  /// from Localizable/state.loading
  ///
  /// In en, this message translates to:
  /// **'Reading your sky…'**
  String get stateLoading;

  /// from Localizable/state.loadingShort
  ///
  /// In en, this message translates to:
  /// **'One moment'**
  String get stateLoadingShort;

  /// from Localizable/state.locked
  ///
  /// In en, this message translates to:
  /// **'Unlock to read'**
  String get stateLocked;

  /// from Localizable/state.needsBirthTime
  ///
  /// In en, this message translates to:
  /// **'This one needs your birth time.'**
  String get stateNeedsBirthTime;

  /// from Localizable/state.nothingToSay
  ///
  /// In en, this message translates to:
  /// **'I couldn\'t read this from your chart, and I won\'t invent it.'**
  String get stateNothingToSay;

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

  /// from Localizable/state.somethingWrong
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Nothing was lost.'**
  String get stateSomethingWrong;

  /// from Localizable/state.unavailable
  ///
  /// In en, this message translates to:
  /// **'Something on our side is not working. It is not you, and it is not your chart.'**
  String get stateUnavailable;

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

  /// from Paywall/paywall.annualNote
  ///
  /// In en, this message translates to:
  /// **'Renews every year until you cancel. Cancel any time in your Apple ID settings.'**
  String get paywallAnnualNote;

  /// from Paywall/paywall.annualTitle
  ///
  /// In en, this message translates to:
  /// **'Everything, for a year'**
  String get paywallAnnualTitle;

  /// from Paywall/paywall.archiveNote
  ///
  /// In en, this message translates to:
  /// **'All eight systems, bought once.'**
  String get paywallArchiveNote;

  /// from Paywall/paywall.archiveTitle
  ///
  /// In en, this message translates to:
  /// **'The whole archive'**
  String get paywallArchiveTitle;

  /// from Paywall/paywall.autoRenewTerms
  ///
  /// In en, this message translates to:
  /// **'Payment is charged to your Apple ID when you confirm. The plan renews automatically unless you cancel at least 24 hours before the period ends, and the renewal is charged within the 24 hours before it. Manage or cancel it in your Apple ID settings.'**
  String get paywallAutoRenewTerms;

  /// from Paywall/paywall.doorNote
  ///
  /// In en, this message translates to:
  /// **'One payment.'**
  String get paywallDoorNote;

  /// from Paywall/paywall.doorSub
  ///
  /// In en, this message translates to:
  /// **'The numbers above are yours. This opens the whole system — every chapter written from your own positions, not from a template.'**
  String get paywallDoorSub;

  /// from Paywall/paywall.everythingSub
  ///
  /// In en, this message translates to:
  /// **'Written from your own positions the first time you open it — your chart, never a template.'**
  String get paywallEverythingSub;

  /// from Paywall/paywall.everythingTitle
  ///
  /// In en, this message translates to:
  /// **'Open the rest of what your chart says'**
  String get paywallEverythingTitle;

  /// from Paywall/paywall.freeNote
  ///
  /// In en, this message translates to:
  /// **'Every calculation stays free, always. What has a price is the writing.'**
  String get paywallFreeNote;

  /// from Paywall/paywall.honestyCancel
  ///
  /// In en, this message translates to:
  /// **'cancel in your Apple ID settings'**
  String get paywallHonestyCancel;

  /// from Paywall/paywall.honestyOnce
  ///
  /// In en, this message translates to:
  /// **'one-time is one-time'**
  String get paywallHonestyOnce;

  /// from Paywall/paywall.honestySeller
  ///
  /// In en, this message translates to:
  /// **'Apple takes the payment and sends the receipt'**
  String get paywallHonestySeller;

  /// from Paywall/paywall.label
  ///
  /// In en, this message translates to:
  /// **'what it costs'**
  String get paywallLabel;

  /// from Paywall/paywall.manage
  ///
  /// In en, this message translates to:
  /// **'Manage your subscription'**
  String get paywallManage;

  /// from Paywall/paywall.manageNote
  ///
  /// In en, this message translates to:
  /// **'Plans bought in the app are cancelled in your Apple ID settings, not here.'**
  String get paywallManageNote;

  /// from Paywall/paywall.monthlyNote
  ///
  /// In en, this message translates to:
  /// **'Transits, the solar return and compatibility while they move, plus 40 questions a month. Renews until you cancel.'**
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

  /// from Paywall/paywall.oneTimeFine
  ///
  /// In en, this message translates to:
  /// **'One payment. Yours permanently. No account needed to buy.'**
  String get paywallOneTimeFine;

  /// from Paywall/paywall.owned
  ///
  /// In en, this message translates to:
  /// **'yours'**
  String get paywallOwned;

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

  /// from Paywall/paywall.perMonthSavings
  ///
  /// In en, this message translates to:
  /// **'{p1} a month · save {p2}%%'**
  String paywallPerMonthSavings(String p1, int p2);

  /// from Paywall/paywall.pitchDoor1
  ///
  /// In en, this message translates to:
  /// **'One payment opens every chapter of this system.'**
  String get paywallPitchDoor1;

  /// from Paywall/paywall.pitchDoor2
  ///
  /// In en, this message translates to:
  /// **'Each chapter is written from your own positions the first time you open it.'**
  String get paywallPitchDoor2;

  /// from Paywall/paywall.pitchDoor3
  ///
  /// In en, this message translates to:
  /// **'Read it whenever you like, in seven languages.'**
  String get paywallPitchDoor3;

  /// from Paywall/paywall.pitchPlan1
  ///
  /// In en, this message translates to:
  /// **'All eight systems stay open while the plan runs.'**
  String get paywallPitchPlan1;

  /// from Paywall/paywall.pitchPlan2
  ///
  /// In en, this message translates to:
  /// **'Transits, the solar return and compatibility are rewritten as the sky moves.'**
  String get paywallPitchPlan2;

  /// from Paywall/paywall.pitchPlan3
  ///
  /// In en, this message translates to:
  /// **'Forty questions a month to Alma, on the deeper voice.'**
  String get paywallPitchPlan3;

  /// from Paywall/paywall.privacy
  ///
  /// In en, this message translates to:
  /// **'Privacy Policy'**
  String get paywallPrivacy;

  /// from Paywall/paywall.refused
  ///
  /// In en, this message translates to:
  /// **'That purchase is not the one that was asked for. Nothing extra has been charged.'**
  String get paywallRefused;

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

  /// from Paywall/paywall.restoredOther
  ///
  /// In en, this message translates to:
  /// **'These purchases already belong to another Alma account. Sign in with that one and they come with you.'**
  String get paywallRestoredOther;

  /// from Paywall/paywall.restoring
  ///
  /// In en, this message translates to:
  /// **'Asking the App Store…'**
  String get paywallRestoring;

  /// from Paywall/paywall.skip
  ///
  /// In en, this message translates to:
  /// **'Not now — take me in'**
  String get paywallSkip;

  /// from Paywall/paywall.storeUnavailable
  ///
  /// In en, this message translates to:
  /// **'The App Store is not answering. Nothing here can be bought until it does — and nothing you already own has changed.'**
  String get paywallStoreUnavailable;

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

  /// from Paywall/paywall.upgradeNote
  ///
  /// In en, this message translates to:
  /// **'The archive, less what you already paid for one system.'**
  String get paywallUpgradeNote;

  /// from Paywall/paywall.upgradeTitle
  ///
  /// In en, this message translates to:
  /// **'The rest of the archive'**
  String get paywallUpgradeTitle;

  /// from Paywall/paywall.verifyLater
  ///
  /// In en, this message translates to:
  /// **'Apple has taken the payment. We could not confirm it this second — it will open by itself shortly, and nothing is lost.'**
  String get paywallVerifyLater;

  /// from Paywall/paywall.weeklyNote
  ///
  /// In en, this message translates to:
  /// **'Try the living layer for one week. Renews weekly until you cancel.'**
  String get paywallWeeklyNote;

  /// from Paywall/paywall.weeklyTitle
  ///
  /// In en, this message translates to:
  /// **'Everything live, weekly'**
  String get paywallWeeklyTitle;

  /// from Paywall/paywall.withdrawn
  ///
  /// In en, this message translates to:
  /// **'Apple has taken that purchase back — refunded or revoked — so nothing is open under it.'**
  String get paywallWithdrawn;

  /// from Screens/scr.addPerson.birthTime
  ///
  /// In en, this message translates to:
  /// **'their birth time'**
  String get scrAddPersonBirthTime;

  /// from Screens/scr.addPerson.birthday
  ///
  /// In en, this message translates to:
  /// **'their birthday'**
  String get scrAddPersonBirthday;

  /// from Screens/scr.addPerson.birthplace
  ///
  /// In en, this message translates to:
  /// **'their birthplace'**
  String get scrAddPersonBirthplace;

  /// from Screens/scr.addPerson.eyebrow
  ///
  /// In en, this message translates to:
  /// **'a second birth'**
  String get scrAddPersonEyebrow;

  /// from Screens/scr.addPerson.lead
  ///
  /// In en, this message translates to:
  /// **'The same five things your own chart needed. Without the minute of birth the comparison still runs, on fewer factors.'**
  String get scrAddPersonLead;

  /// from Screens/scr.addPerson.name
  ///
  /// In en, this message translates to:
  /// **'their name'**
  String get scrAddPersonName;

  /// from Screens/scr.addPerson.namePlaceholder
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get scrAddPersonNamePlaceholder;

  /// from Screens/scr.addPerson.relationPlaceholder
  ///
  /// In en, this message translates to:
  /// **'Partner, mother, friend… (optional)'**
  String get scrAddPersonRelationPlaceholder;

  /// from Screens/scr.addPerson.save
  ///
  /// In en, this message translates to:
  /// **'Save this person'**
  String get scrAddPersonSave;

  /// from Screens/scr.addPerson.saving
  ///
  /// In en, this message translates to:
  /// **'Saving…'**
  String get scrAddPersonSaving;

  /// from Screens/scr.addPerson.timeUnknown
  ///
  /// In en, this message translates to:
  /// **'Birth time unknown'**
  String get scrAddPersonTimeUnknown;

  /// from Screens/scr.addPerson.title
  ///
  /// In en, this message translates to:
  /// **'Add a person'**
  String get scrAddPersonTitle;

  /// from Screens/scr.chat.couldAsk
  ///
  /// In en, this message translates to:
  /// **'you could ask'**
  String get scrChatCouldAsk;

  /// from Screens/scr.chat.moreQuestions
  ///
  /// In en, this message translates to:
  /// **'More questions'**
  String get scrChatMoreQuestions;

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
  /// **'From here the plan carries the conversation — with the morning notification and Alma\'s deeper voice.'**
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
  /// **'{p1} rising. Is that what people meet first?'**
  String scrChatPromptRising(String p1);

  /// from Screens/scr.chat.promptSun
  ///
  /// In en, this message translates to:
  /// **'My Sun is in {p1} — what does that ask of me?'**
  String scrChatPromptSun(String p1);

  /// from Screens/scr.chat.readFromAll
  ///
  /// In en, this message translates to:
  /// **'Show every placement this was read from'**
  String get scrChatReadFromAll;

  /// from Screens/scr.chat.refused
  ///
  /// In en, this message translates to:
  /// **'I could not answer that one without inventing a placement, so I did not. Ask it another way and I will try again.'**
  String get scrChatRefused;

  /// from Screens/scr.chat.rule
  ///
  /// In en, this message translates to:
  /// **'Every answer names the placements it was read from. Nothing here is a prediction.'**
  String get scrChatRule;

  /// from Screens/scr.chat.send
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get scrChatSend;

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

  /// from Screens/scr.chat.thinkingStill
  ///
  /// In en, this message translates to:
  /// **'Still reading — I don\'t skim.'**
  String get scrChatThinkingStill;

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

  /// from Screens/scr.compat.choose
  ///
  /// In en, this message translates to:
  /// **'Compare with somebody else'**
  String get scrCompatChoose;

  /// from Screens/scr.compat.readAgainst
  ///
  /// In en, this message translates to:
  /// **'You and {p1}'**
  String scrCompatReadAgainst(String p1);

  /// from Screens/scr.done
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get scrDone;

  /// from Screens/scr.empty.chapters
  ///
  /// In en, this message translates to:
  /// **'{p1} chapters'**
  String scrEmptyChapters(int p1);

  /// from Screens/scr.empty.example
  ///
  /// In en, this message translates to:
  /// **'what a line looks like'**
  String get scrEmptyExample;

  /// from Screens/scr.empty.exampleNote
  ///
  /// In en, this message translates to:
  /// **'Every sentence Alma writes names the placement it was read from, like the one above. Nothing is a prediction, and nothing is shown that was not calculated.'**
  String get scrEmptyExampleNote;

  /// from Screens/scr.empty.exampleTag
  ///
  /// In en, this message translates to:
  /// **'example — not your chart'**
  String get scrEmptyExampleTag;

  /// from Screens/scr.empty.lead
  ///
  /// In en, this message translates to:
  /// **'Alma computes eight independent systems from a real JPL ephemeris — forty-one chapters in all — and shows you where they agree about you and where they do not.'**
  String get scrEmptyLead;

  /// from Screens/scr.empty.title
  ///
  /// In en, this message translates to:
  /// **'Eight systems, one chart'**
  String get scrEmptyTitle;

  /// from Screens/scr.journey.freeNote
  ///
  /// In en, this message translates to:
  /// **'Everything above is calculated, and calculations are always free. It stays yours whether you read further or not.'**
  String get scrJourneyFreeNote;

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

  /// from Screens/scr.people.consent
  ///
  /// In en, this message translates to:
  /// **'It is their birth data, not yours. Ask them first.'**
  String get scrPeopleConsent;

  /// from Screens/scr.people.eyebrow
  ///
  /// In en, this message translates to:
  /// **'compatibility'**
  String get scrPeopleEyebrow;

  /// from Screens/scr.people.lead
  ///
  /// In en, this message translates to:
  /// **'Compatibility compares your chart against somebody else\'s. The comparison itself is always calculated in full.'**
  String get scrPeopleLead;

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

  /// from Screens/scr.people.saved
  ///
  /// In en, this message translates to:
  /// **'saved'**
  String get scrPeopleSaved;

  /// from Screens/scr.people.title
  ///
  /// In en, this message translates to:
  /// **'People'**
  String get scrPeopleTitle;

  /// from Screens/scr.people.unnamed
  ///
  /// In en, this message translates to:
  /// **'Unnamed'**
  String get scrPeopleUnnamed;

  /// from Screens/scr.saveAccount.body
  ///
  /// In en, this message translates to:
  /// **'Sign in once and your chart and purchases survive a new phone.'**
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

  /// from Screens/scr.signIn.eyebrow
  ///
  /// In en, this message translates to:
  /// **'your account'**
  String get scrSignInEyebrow;

  /// from Screens/scr.signIn.failed
  ///
  /// In en, this message translates to:
  /// **'That did not sign you in. Nothing has changed on your account.'**
  String get scrSignInFailed;

  /// from Screens/scr.signIn.google
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get scrSignInGoogle;

  /// from Screens/scr.signIn.lead
  ///
  /// In en, this message translates to:
  /// **'Signing in attaches a name to the account you already have. Nothing you have read or bought is lost — it is the same account, made durable.'**
  String get scrSignInLead;

  /// from Screens/scr.signIn.linkSent
  ///
  /// In en, this message translates to:
  /// **'Check your inbox. The link signs you in and expires shortly.'**
  String get scrSignInLinkSent;

  /// from Screens/scr.signIn.orEmail
  ///
  /// In en, this message translates to:
  /// **'or by email'**
  String get scrSignInOrEmail;

  /// from Screens/scr.signIn.privacy
  ///
  /// In en, this message translates to:
  /// **'We use your address for the sign-in link and nothing else. There is no newsletter.'**
  String get scrSignInPrivacy;

  /// from Screens/scr.signIn.reason1
  ///
  /// In en, this message translates to:
  /// **'Your chart survives a new phone.'**
  String get scrSignInReason1;

  /// from Screens/scr.signIn.reason2
  ///
  /// In en, this message translates to:
  /// **'Anything you bought can be restored. A purchase belongs to the account that claimed it first, so sign in before you reinstall.'**
  String get scrSignInReason2;

  /// from Screens/scr.signIn.reason3
  ///
  /// In en, this message translates to:
  /// **'There is no password. There never will be.'**
  String get scrSignInReason3;

  /// from Screens/scr.signIn.sendLink
  ///
  /// In en, this message translates to:
  /// **'Send me a link'**
  String get scrSignInSendLink;

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
