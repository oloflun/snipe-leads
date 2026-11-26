# Astryx-kokbok för Snajp CRM

Underlag för den som bygger CRM-gränssnittet enligt
[`docs/crm/DESIGN-CRM.md`](../DESIGN-CRM.md). Gäller **@astryxdesign/core 0.7.17**, det
som ligger i `node_modules`. Klonen i `D:\snajp-crm-forlaga\astryx` är en version
nyare: läs den för hur saker sätts ihop, men lita på typerna i
`node_modules/@astryxdesign/core/dist/<Komponent>/*.d.ts` när de skiljer sig.

Varje prop nedan är kontrollerad mot typdefinitionen i `dist`. Kodexemplen är
typkontrollerade (se slutet av filen för hur). Utseendet är beskrivet från Astryx egna
referensbilder (`.github/visual-baseline/shots`) i neutraltemat; i Snajp byter
`lib/crm/astryx/snajpTema.ts` färger, radier och typsnitt, så formen stämmer men
färgerna blir Snajps.

## Det som gäller överallt

1. **Import per komponent**, aldrig från paketroten:
   `import { Card } from "@astryxdesign/core/Card";`. Underkomponenter och hookar
   importeras från sin familj: `SideNavItem` från `/SideNav`, `GridSpan` från `/Grid`,
   `MetadataListItem` från `/MetadataList`, `useTableSelection` från `/Table`,
   `useHotkeys` från `/hooks`, `useToast` från `/Toast`, `SearchSource` från
   `/Typeahead`. `HStack` och `VStack` finns både som egna vägar och från `/Stack`.
2. **`xstyle` är förbjudet** (kräver StyleX-kompilatorn, som Snajp inte kör). Nästan
   alla komponenter ärver `BaseProps` och tar därför `className`, `style`, `onClick`,
   `data-*` och `aria-*`; de skickas vidare till roten. Använd Tailwind-klasser som läser
   Snajps tokens (`bg-paper2`, `text-ink-muted`, `border-ink/12`) eller `style` med
   `oklch(var(--token))`. Aldrig `#`-färger eller `rgb()`.
3. **Färgnamn är temats, inte CSS:s.** `variant="yellow"`, `color="green"` osv. läser
   `--color-*-yellow` som `snajpTema.ts` pekar på Snajps palett. I dag:
   yellow = ockra (text i `--warning`), green = mossa, blue = **sigill** (`--seal`).
   Kontraktet vill ha Bolag i `--chart-blue`: ändra temat, inte komponenten.
4. **Avståndsskalan** för `gap`, `padding`, `contentPadding` m.fl. är stegen
   `0 | 0.5 | 1 | 1.5 | 2 | 3 | 4 | 5 | 6 | 8 | 10`, ett steg = 4 px (4 = 16 px).
   Andra tal är typfel.
5. **Ikoner: två sorters `icon`-props** (typkontrollen fällde fem exempel på detta).
   - Typen `ReactNode | IconType` tar lucide-komponenten direkt (`icon={Building2}`),
     ett element eller ett semantiskt namn (`icon="search"`): `SideNavItem.icon`,
     `selectedIcon`, `NavHeadingMenuItem.icon`, `DropdownMenuItem.icon` (och
     `items`-raderna), `SelectorOption.icon`, `TextInput.startIcon`,
     `Selector.startIcon`, `Switch.labelIcon`, `CheckboxInput.labelIcon`, och
     `Icon.icon` (som bara tar komponent eller namn).
   - Typen `ReactNode` tar **bara ett element**: `Button.icon`, `IconButton.icon`,
     `Token.icon`, `Badge.icon`, `Tab.icon`, `SegmentedControlItem.icon`,
     `EmptyState.icon`, `MetadataListItem.icon`, `Banner.icon`, `NavIcon.icon`,
     `SideNavHeading.icon`. Skriv `icon={<Icon icon={Plus} size="sm" />}`. En
     komponent ger typfel; en sträng som `"search"` ger inget typfel men **ritas som
     texten "search"**.

   De semantiska namnen i 0.7.17: `close`, `chevronDown`, `chevronLeft`, `chevronRight`,
   `chevronsLeft`, `chevronsRight`, `check`, `success`, `error`, `warning`, `info`,
   `calendar`, `clock`, `externalLink`, `menu`, `moreHorizontal`, `search`, `upload`,
   `arrowUp`, `arrowDown`, `arrowsUpDown`, `funnel`, `eyeSlash`, `viewColumns`, `copy`,
   `checkDouble`, `wrench`, `stop`, `microphone`. Allt annat: lucide-komponenten.
6. **Tvåspråkigt.** Varje `label`, `title`, `heading`, `placeholder`, `aria-label` och
   tomtext går genom `useLocale().text({ sv, en })`. Astryx egna standardtexter
   (Unselect All, No results, Close popover …) översätts av `ASTRYX_SVENSKA` i
   `CrmRam.tsx` bara där en nyckel finns: skicka hellre egen text via propen
   (`clearLabel`, `emptySearchText`, `label`).
7. **Generiska tabelltyper kräver `type`, inte `interface`.** `Table`, `TableColumn`
   och tabellhookarna kräver `T extends Record<string, unknown>`. Ett `type Bolag = {…}`
   (som i `lib/crm/api.ts`) uppfyller det; ett `interface Bolag {…}` gör det inte.
8. **Inget renderas utan ramen.** Allt nedan förutsätter att `CrmRam` ligger runt
   (`Theme`, `InternationalizationProvider`, `LinkProvider` med `next/link`). Utan
   `LinkProvider` blir varje `href` en hel sidladdning.

---

## Skal och navigering

### AppShell

```tsx
import { AppShell } from "@astryxdesign/core/AppShell";
import { SideNav, SideNavHeading } from "@astryxdesign/core/SideNav";

export function Skal({ children }: { children: React.ReactNode }) {
  return (
    <AppShell
      variant="elevated"
      contentPadding={0}
      height="fill"
      mobileNav={{ breakpoint: "md" }}
      sideNav={<SideNav header={<SideNavHeading heading="Snajp" />}>{null}</SideNav>}
    >
      {children}
    </AppShell>
  );
}
```

- **Ser ut:** `elevated` (standard) ger navigeringen tvättens bakgrund och innehållet
  ett upphöjt blad med stort rundat hörn uppe till vänster mot navigeringen (referensen:
  grå rail, vitt blad med radie cirka 24 px). `section` ger en hårlinje i stället för
  bladet, `wash` och `surface` ger platt bakgrund.
- **Props:** `variant` (`wash | surface | section | elevated`), `contentPadding`
  (avståndssteg, standard `0`), `sideNav`, `topNav`, `banner`, `height`
  (`fill` = 100dvh med egen rullning i innehållet, `auto` = sidan rullar),
  `mobileNav` (`false`, ett `MobileNavConfig` eller en egen `<MobileNav>`).
- **`MobileNavConfig`:** `{ breakpoint?: "sm"|"md"|"lg"|"xl"|"2xl"|"none", hasToggle?,
  isOpen?, onOpenChange?, content?, defaultIsMobile? }`. Standard `breakpoint` är `md`.
- **Mobil utan `topNav`:** under brytpunkten ritar AppShell själv en toppremsa med
  `SideNav` i "topbar"-läge (rubriken plus `footerIcons`) och en hamburgare; lådan får
  sidnavigeringens innehåll. Ingen egen `MobileNav` behövs.
- **Fällor:**
  - `contentPadding` är ett avståndssteg, inte pixlar: `contentPadding={6}` = 24 px.
    Tabellsidor vill ha `0` och egen marginal i sidhuvudet.
  - Skicka aldrig en komponent som renderar `null` som `sideNav`: AppShell tror då att
    det finns en sidnavigering. Skicka `undefined`.
  - `defaultIsMobile` bara om servern vet att det är en telefon; annars blinkar
    skrivbordslayouten fram först.
  - `useAppShellMobile()` (från `/AppShell`) ger `{ isMobile, closeMobileNav, … }` för
    att stänga lådan efter en egen navigering.
  - Bladets rundning och skugga styrs av temats `--radius-page` och skuggtokens, inte
    av props.

### SideNav, SideNavSection, SideNavItem

```tsx
import { Building2, Users } from "lucide-react";
import { Kbd } from "@astryxdesign/core/Kbd";
import { SideNav, SideNavHeading, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
import { useLocale } from "@/lib/i18n";

export function Navigering({ aktiv, oppnaPalett }: { aktiv: string; oppnaPalett: () => void }) {
  const { text } = useLocale();
  return (
    <SideNav
      collapsible
      header={<SideNavHeading heading="Snajp" />}
      topContent={
        <SideNavItem
          label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
          icon="search"
          onClick={oppnaPalett}
          endContent={<Kbd keys="mod+k" />}
        />
      }
    >
      <SideNavSection title={text({ sv: "Arbetsyta", en: "Workspace" })}>
        <SideNavItem
          label={text({ sv: "Bolag", en: "Companies" })}
          href="/crm/bolag"
          icon={Building2}
          isSelected={aktiv === "bolag"}
          endContent={<span className="tabular-nums text-ink-muted">73</span>}
        />
        <SideNavItem label={text({ sv: "Personer", en: "People" })} href="/crm/personer" icon={Users} />
      </SideNavSection>
    </SideNav>
  );
}
```

- **Ser ut:** ljus kolumn; sektionsrubrik i liten halvfet dämpad text; varje post är en
  rad med ikon och text, vald post är en mjuk rundad platta i bredd med kolumnen och
  halvfet text. Antal till höger som en liten grå pillerplatta när `endContent` är en
  `Badge`/text.
- **SideNav props:** `header`, `topContent` (under rubriken, ovanför sektionerna),
  `children`, `footer` (ovanför ikonraden), `footerIcons`, `collapsible`
  (`true` eller `{ defaultIsCollapsed, isCollapsed, onCollapsedChange, hasButton,
  buttonLabel }`), `resizable` (`true` eller `{ defaultWidth, minWidth, maxWidth,
  autoSaveId, … }`).
- **SideNavSection props:** `title` (krävs, sträng), `subtitle`, `endContent`,
  `isHeaderHidden` (döljer rubriken visuellt men behåller den för skärmläsare).
- **SideNavItem props:** `label` (krävs, sträng), `href` eller `onClick`, `icon`,
  `selectedIcon`, `isSelected`, `isDisabled`, `endContent` (bara passivt innehåll:
  antal, `Kbd`, `StatusDot`), `actions` (knappar och menyer på raden), `children`
  (undernivå) med `collapsible`, `size` (`sm | md | lg`).
- **Fällor:**
  - Det finns ingen bredd-prop för 248 px. Bredden är temats (sidnavigeringens token)
    eller `resizable={{ defaultWidth: 248, minWidth: 248, maxWidth: 248 }}`.
  - Valt läge räknas inte ut från URL:en: `isSelected` måste sättas av den som
    renderar (läs `usePathname()`).
  - Interaktiva saker får inte ligga i `endContent`; de går i `actions`.
  - Hopfällt visas bara ikoner: varje post behöver en `icon`, annars blir raden tom.
  - Avdelare mellan sektioner: `<Divider />` direkt bland barnen (så gör mallen
    `shell-side-nav`).
  - `SideNavCollapseButton` (från `/SideNav`) finns om knappen ska ligga någon annanstans.

### SideNavHeading med meny (arbetsyteväxlaren)

```tsx
import { Search, Settings, ArrowLeft } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { NavHeadingMenu, NavHeadingMenuItem } from "@astryxdesign/core/NavMenu";
import { SideNavHeading } from "@astryxdesign/core/SideNav";
import { useLocale } from "@/lib/i18n";

export function Arbetsytevaxlare({ namn, oppnaPalett }: { namn: string; oppnaPalett: () => void }) {
  const { text } = useLocale();
  return (
    <SideNavHeading
      heading={namn}
      icon={<Avatar name={namn} size={24} shape="rounded" tooltip={false} />}
      menu={
        <NavHeadingMenu>
          <NavHeadingMenuItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
          <NavHeadingMenuItem label={text({ sv: "Inställningar", en: "Settings" })} href="/installningar" icon={Settings} />
        </NavHeadingMenu>
      }
      headerEndContent={
        <IconButton
          label={text({ sv: "Sök", en: "Search" })}
          icon={<Icon icon={Search} size="sm" />}
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            oppnaPalett();
          }}
        />
      }
    />
  );
}
```

- **Ser ut:** ikon (här en rundad fyrkantig avatar med initialen), namnet i halvfet, en
  vinkel nedåt. Klick öppnar en popover under rubriken med menyraderna.
- **Props:** `heading` (krävs, sträng), `icon`, `headingHref`, `superheading`,
  `subheading` (+ `…Href`), `menu`, `headerEndContent` (döljs hopfällt).
- **Fällor:**
  - Lägg menyn i `NavHeadingMenu` med `NavHeadingMenuItem` (från `/NavMenu`): de ger
    `role="menu"`, piltangenter och stänger popovern vid val. `ListItem` (som ett av
    Astryx exempel visar) stänger den inte.
  - Utan `headingHref` är **hela rubriken** menyknappen. Ett klick på en knapp i
    `headerEndContent` bubblar dit och öppnar menyn också: anropa
    `e.stopPropagation()` i knappens `onClick`, som ovan.
  - Med `headingHref` blir namnet en länk och bara vinkeln öppnar menyn.
  - `heading` är en sträng, inte JSX.

### NavIcon

```tsx
import { Sparkles } from "lucide-react";
import { Icon } from "@astryxdesign/core/Icon";
import { NavIcon } from "@astryxdesign/core/NavIcon";

export function Produktikon() {
  return <NavIcon icon={<Icon icon={Sparkles} size="sm" />} />;
}
```

- **Ser ut:** en rund platta i accentfärg (i referensen svart cirkel med vit ikon) som
  står före produktnamnet i `SideNavHeading`/`TopNavHeading`.
- **Props:** bara `icon` (krävs, ett element).
- **Fälla:** alltid rund och alltid accentfärgad. Kontraktets fyrkantiga bläckplatta med
  initial är en `Avatar shape="rounded"`, inte `NavIcon`.

### MobileNav och MobileNavToggle

```tsx
import { AppShell } from "@astryxdesign/core/AppShell";
import { MobileNav, MobileNavToggle } from "@astryxdesign/core/MobileNav";

export function EgenMobil({ meny, children }: { meny: React.ReactNode; children: React.ReactNode }) {
  return (
    <AppShell sideNav={meny} mobileNav={<MobileNav header="Snajp" width={320}>{meny}</MobileNav>}>
      <MobileNavToggle label="Meny" />
      {children}
    </AppShell>
  );
}
```

- **Ser ut:** låda från vänster (320 px, högst 85vw) med rubrik och stängknapp, över en
  dämpning.
- **MobileNav props:** `isOpen`, `onOpenChange`, `children` (krävs), `header`, `width`
  (standard 320), `side` (`start | end | auto`), `label`.
- **MobileNavToggle props:** `label` (standard "Open navigation"), `children`.
- **Fälla:** CRM:et behöver inte detta. AppShell bygger mobillådan av `sideNav` själv
  (se AppShell). Skickar du en egen `MobileNav` äger du öppet läge och knapp själv.

### DropdownMenu och MoreMenu

```tsx
import { Pencil, Trash2 } from "lucide-react";
import { DropdownMenu, type DropdownMenuOption } from "@astryxdesign/core/DropdownMenu";
import { MoreMenu } from "@astryxdesign/core/MoreMenu";
import { useLocale } from "@/lib/i18n";

export function Menyer({ redigera, taBort }: { redigera: () => void; taBort: () => void }) {
  const { text } = useLocale();
  const val: DropdownMenuOption[] = [
    { label: text({ sv: "Redigera", en: "Edit" }), icon: Pencil, onClick: redigera },
    { type: "divider" },
    { label: text({ sv: "Ta bort", en: "Delete" }), icon: Trash2, variant: "destructive", onClick: taBort }
  ];
  return (
    <>
      <DropdownMenu button={{ label: text({ sv: "Sortera", en: "Sort" }), variant: "ghost", size: "sm" }} items={val} />
      <MoreMenu label={text({ sv: "Fler val", en: "More options" })} items={val} alignment="end" />
    </>
  );
}
```

- **Ser ut:** `DropdownMenu` är en knapp med vinkel; `MoreMenu` en spökknapp med tre
  prickar. Menyn är en rundad popover med rader (ikon, text, beskrivning), avdelare och
  rubricerade sektioner; den förstörande raden i felfärg.
- **Radformen `DropdownMenuOption`:** en rad `{ label, icon?, onClick?, href?,
  description?, endContent?, isDisabled?, variant?: "default"|"destructive",
  hasCloseOnSelect?, id?, items? }` (med `items` blir raden en undermeny), en avdelare
  `{ type: "divider" }` eller en sektion `{ type: "section", title?, items }`.
- **DropdownMenu props:** `items` (krävs), `button` (Button-props utom `onClick`; standard
  `{ label: "Menu" }`), `renderTrigger` (egen utlösare: sprid alla props den får på
  elementet), `hasChevron`, `placement`, `alignment`, `menuWidth`, `header`, `footer`,
  `isMenuOpen`/`onOpenChange`, `presentation` (`popover | bottom-sheet | adaptive`).
- **MoreMenu props:** `items` (krävs), `label` (tooltip och aria), `variant`, `size`,
  `icon`, `isDisabled`, `placement`, `alignment`, `presentation`.
- **Fällor:** knappens text i `DropdownMenu` står i `button.label`, inte i en egen
  `label`-prop. Ett val som inte gör något får inte finnas (kontraktet).

---

## Kommandopalett och tangenter

### CommandPalette med delkomponenter

```tsx
import { useMemo, useState } from "react";
import { CommandPalette, CommandPaletteFooter, CommandPaletteInput } from "@astryxdesign/core/CommandPalette";
import { createStaticSource, type SearchableItem } from "@astryxdesign/core/Typeahead";
import { useHotkeys } from "@astryxdesign/core/hooks";
import { useLocale } from "@/lib/i18n";

type Kommando = SearchableItem<{ group: string; href: string }>;

export function EnkelPalett({ ga }: { ga: (href: string) => void }) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState(false);
  useHotkeys([{ keys: "mod+k", onPress: () => setOppen((o) => !o), allowInInputs: true }]);
  const kalla = useMemo(
    () =>
      createStaticSource<Kommando>([
        { id: "bolag", label: text({ sv: "Bolag", en: "Companies" }), auxiliaryData: { group: text({ sv: "Gå till", en: "Go to" }), href: "/crm/bolag" } }
      ]),
    [text]
  );
  return (
    <CommandPalette<Kommando>
      isOpen={oppen}
      onOpenChange={setOppen}
      searchSource={kalla}
      label={text({ sv: "Kommandopalett", en: "Command palette" })}
      input={<CommandPaletteInput placeholder={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })} />}
      footer={<CommandPaletteFooter />}
      emptySearchText={text({ sv: "Inga träffar", en: "No results" })}
      onValueChange={(id) => ga(`/crm/${id}`)}
    />
  );
}
```

- **Ser ut:** en modal dialog, 640 px bred och högst 480 px hög, överst ett sökfält,
  därunder grupprubriker i liten dämpad text och träffrader; den markerade raden är en
  ljus rundad platta (mörkare när den är vald). Längst ned en fot med tangenttips
  (pilar, Enter, Esc) som `Kbd`.
- **CommandPalette props:** `isOpen`, `onOpenChange`, `searchSource` (alla tre krävs),
  `input` (standard `<CommandPaletteInput />`), `footer` (standard
  `<CommandPaletteFooter />`), `renderItem(item, isSelected)`, `emptySearchText`,
  `emptyBootstrapText`, `value`/`onValueChange`, `label`, `width` (640), `maxHeight`
  (480), `isInline`.
- **Delkomponenter (alla från `/CommandPalette`):**
  - `CommandPaletteInput`: `placeholder`, `label`, `hasAutoFocus`, `endContent`.
  - `CommandPaletteFooter`: `children` (ersätter tangenttipsen).
  - `CommandPaletteList`, `CommandPaletteGroup` (`heading` krävs),
    `CommandPaletteItem` (`value` krävs, `onSelect`, `isDisabled`),
    `CommandPaletteEmpty`: används **inte** med `searchSource`. Paletten bygger listan,
    grupperna och tomläget själv; delarna finns för den som bygger en egen lista.
- **Så fungerar den:**
  - Grupper: lägg `auxiliaryData.group` (en sträng) på varje träff. Paletten grupperar i
    den ordning grupperna först dyker upp; träffar utan grupp hamnar sist.
  - Val: Enter eller klick anropar `onValueChange(item.id)` och **stänger paletten
    själv**. Gör navigeringen i `onValueChange`.
  - Tom fråga anropar `bootstrap()`, varje tangent anropar `search(fråga)`.
- **Fällor:**
  - `searchSource` måste vara stabil (`useMemo`). En ny källa medan paletten är öppen
    kör om sökningen.
  - Paletten debouncar inte. Gör det i källan och avbryt gamla anrop i `cancel()` (se
    recept c).
  - `renderItem` får bara returnera passivt innehåll (text, ikon, avatar, `Kbd`),
    inga knappar eller länkar.
  - Medan svaret dröjer filtrerar paletten de förra träffarna på `label` för att det ska
    kännas direkt; sätt därför `label` till det man söker på (bolagsnamnet).
  - Ett anrop som kastar blir en tom träfflista, inte ett felmeddelande.
  - `id` måste vara unikt över alla grupper: prefixa (`gå:bolag`, `bolag:<uuid>`).

### useHotkeys

```tsx
import { useHotkeys } from "@astryxdesign/core/hooks";

export function Snabbtangent({ oppna }: { oppna: () => void }) {
  useHotkeys([
    { keys: "mod+k", onPress: oppna, allowInInputs: true },
    { keys: "ctrl+k", onPress: oppna, allowInInputs: true }
  ]);
  return null;
}
```

- **Signatur:** `useHotkeys(hotkeys: Hotkey[]): void` där `Hotkey = { keys, onPress,
  allowInInputs?, isDisabled? }`. En lyssnare på `window`, `preventDefault()` vid
  träff, den **första** matchande posten vinner.
- **`mod`** = ⌘ på Apple, Ctrl annars. Kontraktet vill ha både Ctrl K och Cmd K: med
  `mod+k` plus `ctrl+k` fungerar Ctrl K också på Mac, och på Windows matchar `mod+k`
  först så inget körs två gånger.
- **Fällor:**
  - Utan `allowInInputs: true` fungerar genvägen inte när fokus står i ett sökfält.
  - Avregistrera inte genom att avmontera; använd `isDisabled`.
  - Skiftade tecken skrivs som tecknet: `"?"`, inte `"shift+/"`.

### Kbd

```tsx
import { Kbd } from "@astryxdesign/core/Kbd";

export function Genvag() {
  return <Kbd keys="mod+k" />;
}
```

- **Ser ut:** små ljusgrå rundade tangentplattor, en per tangent ("Ctrl" "K" på Windows,
  "⌘" "K" på Mac).
- **Props:** `keys` (krävs; `+` mellan tangenterna; `mod`, `ctrl`, `alt`, `shift`,
  `meta`, `enter`, `escape`/`esc`, `tab`, piltangenter; `plus` för ett "+").
- **Fälla:** samma sträng som i `useHotkeys`, så att det som visas är det som gäller.

---

## Poster, etiketter och status

### Avatar

```tsx
import { Avatar } from "@astryxdesign/core/Avatar";

export function Avatarer() {
  return (
    <>
      <Avatar name="Byggbolaget Norr" size="sm" shape="rounded" tooltip={false} className="crm-avatar-bla" />
      <Avatar name="Anna Lind" size="xsm" />
    </>
  );
}
```

- **Ser ut:** rund (standard), `rounded` (rundad fyrkant) eller `square`. Utan bild en
  ljusgrå platta med initialer i mörk text (referensen: "JD" på grå cirkel).
- **Props:** `name` (initialer, alt-text och tooltip), `src`, `fallbackSrc`, `size`,
  `shape` (`circle | rounded | square`), `status` (hörninnehåll, typiskt
  `AvatarStatusDot`), `tooltip` (standard `true` = namnet visas vid hovring), `href`/`as`,
  `onClick` (blir då en knapp).
- **Storlekar:** `xsm` 20, `sm` 24, `md` 36, `lg` 48, `xl` 128, eller exakt ett av
  `16 20 24 32 36 40 48 60 64 72 96 128 144 180`. **22 och 44 (kontraktets mått) finns
  inte**: använd 20 eller 24 i tabellen och 40 eller 48 i panelen.
- **Initialer:** första och **sista** ordets första tecken, versalt. "Byggbolaget Norr
  AB" blir "BA": skicka namnet utan bolagsform (`AB`, `HB`, `KB`, `Ek. för.`).
- **Färg:** det finns **ingen färg-prop**. Initialplattan är elementet
  `.astryx-avatar-fallback` inuti roten. Ge roten en klass och färga plattan i CSS:
  `.crm-avatar-bla .astryx-avatar-fallback { background-color: oklch(var(--chart-blue) / 0.14); color: oklch(var(--ink)); }`.
  Verifiera i bild att regeln vinner över Astryx lager.
- **Fällor:** `tooltip` är på som standard: stäng av den i postchips där namnet redan
  står bredvid. `onClick` på Avatar inuti en knapp ger knapp i knapp.

### AvatarGroup

```tsx
import { Avatar } from "@astryxdesign/core/Avatar";
import { AvatarGroup, AvatarGroupOverflow } from "@astryxdesign/core/AvatarGroup";

export function Ansvariga({ namn }: { namn: string[] }) {
  return (
    <AvatarGroup size="xsm">
      {namn.slice(0, 3).map((n) => (
        <Avatar key={n} name={n} />
      ))}
      {namn.length > 3 ? <AvatarGroupOverflow count={namn.length - 3} /> : null}
    </AvatarGroup>
  );
}
```

- **Ser ut:** överlappande avatarer, sist en "+N"-platta.
- **Props:** `children` (krävs: `Avatar` och högst en `AvatarGroupOverflow`), `size`,
  `shape` (vinner över varje avatars egen).
- **AvatarGroupOverflow:** `count` (krävs), `children` (egen text), `onClick`.
- **Fälla:** gruppen skär inte själv; du väljer vilka som syns med `slice`.

### Token

```tsx
import { Globe, Mail } from "lucide-react";
import { Icon } from "@astryxdesign/core/Icon";
import { Token } from "@astryxdesign/core/Token";

export function Lankpiller() {
  return (
    <>
      <Token label="byggnorr.se" icon={<Icon icon={Globe} size="sm" />} href="https://byggnorr.se" size="sm" />
      <Token label="info@byggnorr.se" icon={<Icon icon={Mail} size="sm" />} href="mailto:info@byggnorr.se" size="sm" />
    </>
  );
}
```

- **Ser ut:** liten ljusgrå rundad platta med text (referensen: "Token" på grå platta,
  radie cirka 6 px; i Snajps tema helt rundad). Med `onRemove` ett litet kryss.
- **Props:** `label` (krävs, sträng), `size` (`sm | md | lg`), `color` (`default red
  orange yellow green teal cyan blue purple pink gray`), `icon`, `href`, `onClick`,
  `onRemove`, `endContent`, `isDisabled`, `description`, `isLabelHidden`.
- **Fällor:** `label` är en sträng; vill du ha en avatar i pillret går den i `icon`.
  Token har ingen `target`-prop: en webbplats som ska öppnas i ny flik behöver
  `onClick` med `window.open(url, "_blank", "noopener")` i stället för `href`.
  `mailto:` och `tel:` fungerar med `href`.

### Badge

```tsx
import { Badge } from "@astryxdesign/core/Badge";
import { StatusDot } from "@astryxdesign/core/StatusDot";
import { useLocale } from "@/lib/i18n";

export function Relation() {
  const { text } = useLocale();
  const kund = text({ sv: "Kund", en: "Customer" });
  return <Badge variant="green" label={kund} icon={<StatusDot variant="success" label={kund} />} />;
}
```

- **Ser ut:** litet helt rundat piller med tonad bakgrund och text i samma ton
  (referensen: "Badge" på grått piller, cirka 20 px högt).
- **Props:** `label` (krävs, ReactNode), `variant` (`neutral info success warning error
  blue cyan green orange pink purple red teal yellow`), `icon`.
- **Fällor:** **Badge har ingen `gray`** (Token, Card och Icon har det): grå etikett är
  `variant="neutral"`. `BolagVy.tsx` i commit `b6c08ef2` skickar `"gray"` till Badge och
  fälls av en typkontroll. Ingen `size`-prop. Badge är för status och kategori, inte för tal, datum
  eller antal (Astryx egen regel); antal i ett sidhuvud är en neutral `Badge` bara om
  kontraktet säger så, annars `Text`.

### StatusDot

```tsx
import { StatusDot } from "@astryxdesign/core/StatusDot";

export function Synkstatus() {
  return <StatusDot variant="accent" label="Pågår" isPulsing tooltip="Synken körs" />;
}
```

- **Ser ut:** en liten fylld prick, cirka 8 px (referensen: grön prick).
- **Props:** `variant` (krävs: `success | warning | error | accent | neutral`), `label`
  (krävs, aria-label), `isPulsing`, `tooltip`, `icon`.
- **Fällor:** bara fem färger. Kontraktets "mineral" och "blå" finns inte som variant:
  ge pricken en klass och färga den i CSS, eller låt `Badge`-varianten bära färgen.
  `label` syns inte; skriv alltid ut texten bredvid. Astryx exempel i `TableColumn`
  använder `status=` och saknar `label`: det är fel, propen heter `variant`.

### AvatarStatusDot

```tsx
import { Avatar, AvatarStatusDot } from "@astryxdesign/core/Avatar";

export function Inloggad() {
  return <Avatar name="Anna Lind" size="md" status={<AvatarStatusDot variant="success" label="Aktiv" />} />;
}
```

- **Props:** `variant` (`success | neutral | error`), `label`, `icon`. Storleken följer
  avataren.

---

## Ytor och layout

### Card

```tsx
import { Card } from "@astryxdesign/core/Card";
import { Text } from "@astryxdesign/core/Text";

export function Kort() {
  return (
    <Card variant="yellow" padding={5} elevation="none">
      <Text type="label" color="secondary">Att rätta</Text>
    </Card>
  );
}
```

- **Ser ut:** `default` är en vit yta med hårlinjeram och rundade hörn (temats
  `--radius-container`, Snajp 16 px). Färgvarianterna är tonade plattor utan ram.
- **Props:** `variant` (`default transparent muted blue cyan gray green orange pink
  purple red teal yellow`), `padding` (avståndssteg; utelämnad = temats kortpadding,
  inte ett fast steg), `elevation` (`none | low | med | high`), `width`, `height`,
  `maxWidth`, `minHeight`, `children`.
- **Fällor:** Card är inte klickbart på riktigt; för ett kort som länkar, använd
  `ClickableCard`. Ram ritas bara för `default`. Astryx regel: kort för saker som går att
  flytta eller ta bort var för sig; en sidregion är `Section`.

### ClickableCard

```tsx
import { ClickableCard } from "@astryxdesign/core/ClickableCard";
import { Text } from "@astryxdesign/core/Text";
import { useLocale } from "@/lib/i18n";

export function Lankkort() {
  const { text } = useLocale();
  return (
    <ClickableCard label={text({ sv: "Att rätta, till Synk", en: "To fix, open Sync" })} href="/crm/synk" variant="yellow" padding={5}>
      <Text type="label">{text({ sv: "Att rätta", en: "To fix" })}</Text>
    </ClickableCard>
  );
}
```

- **Ser ut:** som `Card` (referensen: vit yta, hårlinje, radie cirka 12 px, rubrik och
  dämpad rad) med hovringsplatta och fokusring över hela kortet.
- **Props:** `label` (krävs, tillgängligt namn), `href` eller `onClick`, `target`,
  `isDisabled`, `padding` (standard 4), `variant`, `elevation`, `width`, `height`,
  `maxWidth`.
- **Fälla:** `onClick` gäller bara ytan; knappar inuti kortet fungerar för sig.

### SelectableCard

```tsx
import { useState } from "react";
import { SelectableCard } from "@astryxdesign/core/SelectableCard";

export function Valkort() {
  const [vald, setVald] = useState(false);
  return (
    <SelectableCard label="Fortnox" isSelected={vald} onChange={setVald}>
      Fortnox
    </SelectableCard>
  );
}
```

- **Ser ut:** kort som får accentram (ockra i Snajp) när det är valt.
- **Props:** `label`, `isSelected`, `onChange` (alla krävs), `isDisabled`, `padding`,
  `variant`, `elevation`, `width`, `height`, `maxWidth`.
- **Fälla:** för val, inte navigering.

### Grid och GridSpan

```tsx
import { Card } from "@astryxdesign/core/Card";
import { Grid, GridSpan } from "@astryxdesign/core/Grid";

export function Rutnat() {
  return (
    <Grid columns={{ minWidth: 220, max: 4 }} gap={4}>
      <Card />
      <Card />
      <GridSpan columns={2}>
        <Card />
      </GridSpan>
    </Grid>
  );
}
```

- **Props Grid:** `columns` (`number` = exakt N kolumner som aldrig bryts om, eller
  `{ minWidth, max?, repeat?: "fill" | "fit" }` som bryts om), `gap`, `rowGap`,
  `columnGap`, `rowHeight` (px), `align`, `justify`, `width`, `height`, `maxWidth`,
  `minHeight`.
- **Props GridSpan:** `columns` (`number | "full"`), `rows`, `className`, `style`.
- **Fällor:**
  - Ett numeriskt `columns={4}` bryts aldrig om och spränger mobilen. Använd objektet.
  - Fyra kort med `{ minWidth, max: 4 }` blir 3 + 1 på mellanbredder. Astryx
    `dashboard`-mall lägger två rutnät med två kort i ett yttre rutnät
    (`{ minWidth: 320, max: 2, repeat: "fit" }`) så att det blir 4, 2 + 2 eller 1.
  - `GridSpan columns={2}` i ett rutnät som just då har en kolumn skapar en implicit
    andra kolumn. Kontrollera 390 px.

### Section

```tsx
import { Section } from "@astryxdesign/core/Section";

export function Region({ children }: { children: React.ReactNode }) {
  return (
    <Section variant="transparent" padding={6} paddingBlockEnd={4} dividers={["bottom"]}>
      {children}
    </Section>
  );
}
```

- **Props:** `variant` (`section | transparent | muted`), `padding` (standard 4),
  `paddingInline`, `paddingInlineStart`, `paddingInlineEnd`, `paddingBlock`,
  `paddingBlockStart`, `paddingBlockEnd`, `dividers` (`top bottom start end`), `width`,
  `height`, `maxWidth`, `minHeight`.
- **Fälla:** centrering (`marginInline: auto`) gör Astryx med `xstyle`; i Snajp med
  `className="mx-auto"`.

### Divider

```tsx
import { Divider } from "@astryxdesign/core/Divider";

export function Avdelare() {
  return <Divider variant="subtle" />;
}
```

- **Props:** `orientation` (`horizontal | vertical`), `label` (centrerad text),
  `variant` (`subtle | strong`), `isFullBleed` (når behållarens kanter).
- **Fälla:** vertikal avdelare i en `HStack` behöver att stacken sträcker barnen
  (`HStack` gör det som standard: `vAlign="stretch"`).

### Layout, LayoutHeader, LayoutContent, LayoutFooter, LayoutPanel

```tsx
import { Layout, LayoutContent, LayoutFooter, LayoutHeader, LayoutPanel } from "@astryxdesign/core/Layout";

export function Sidlayout() {
  return (
    <Layout
      height="fill"
      header={<LayoutHeader hasDivider padding={6} paddingBlockEnd={0}>rubrik</LayoutHeader>}
      content={<LayoutContent padding={0}>innehåll</LayoutContent>}
      end={<LayoutPanel width={320} hasDivider>panel</LayoutPanel>}
      footer={<LayoutFooter hasDivider>fot</LayoutFooter>}
    />
  );
}
```

- **Layout props:** `header`, `content` (eller `children`), `footer`, `start`, `end`,
  `height` (`fill | auto`), `contentWidth` (maxbredd, centrerad), `padding`,
  `defaultHasDividers`.
- **LayoutHeader:** `hasDivider`, `height`, `padding`, `paddingBlockEnd` (0 lägger en
  `TabList` direkt mot avdelaren), `label`, `role`.
- **LayoutContent:** `padding`, `isScrollable` (standard `true`), `label`, `role`.
- **LayoutFooter:** `hasDivider`, `height`, `padding`, `label`, `role`.
- **LayoutPanel:** `width`, `hasDivider`, `padding`, `isScrollable`, `resizable`.
- **Fällor:** `LayoutContent` rullar själv; lägg inte en egen `overflow-auto` runt.
  I `Dialog` och `Drawer` är `Layout` det kontrakterade sättet att få huvud, rullande
  innehåll och fot (aldrig `padding={0}` på dialogen).

### Stack, HStack, VStack, StackItem

```tsx
import { HStack, StackItem, VStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";

export function Rad() {
  return (
    <VStack gap={1}>
      <HStack gap={2} vAlign="center">
        <StackItem size="fill">
          <Text weight="semibold">Bolag</Text>
        </StackItem>
        <Text color="secondary">73</Text>
      </HStack>
    </VStack>
  );
}
```

- **Props:** `gap`, `padding` och alla `padding…`-varianter, `hAlign`, `vAlign`
  (`justify`/`align` är alias), `wrap`, `width`, `height`, `maxWidth`, `minHeight`,
  `isScrollable`, `as`, `className`, `style`. `Stack` har dessutom `direction`.
- **StackItem:** `size` (`static | fill`), `crossAlignSelf`, `isScrollable`.
- **Fällor:**
  - `HStack` har `vAlign="stretch"` som standard: en ikon bredvid text hamnar i
    överkant. Skriv `vAlign="center"` på varje rad med ikon och text.
  - `VStack` har `hAlign="stretch"`: knappar blir fullbreda. Använd `hAlign="start"`.
  - Det finns ingen `flex: 1`-prop; använd `StackItem size="fill"`.

---

## Data och detaljer

### MetadataList och MetadataListItem

```tsx
import { Building2, Phone } from "lucide-react";
import { Icon } from "@astryxdesign/core/Icon";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { useLocale } from "@/lib/i18n";

export function Falt() {
  const { text } = useLocale();
  return (
    <MetadataList title={text({ sv: "Allmänt", en: "General" })} label={{ position: "start", width: 140 }}>
      <MetadataListItem label={text({ sv: "Org.nr", en: "Org. no." })} icon={<Icon icon={Building2} size="sm" color="secondary" />}>
        556677-8899
      </MetadataListItem>
      <MetadataListItem label={text({ sv: "Telefon", en: "Phone" })} icon={<Icon icon={Phone} size="sm" color="secondary" />}>
        070-123 45 67
      </MetadataListItem>
    </MetadataList>
  );
}
```

- **Ser ut:** rader med dämpad etikett till vänster och värdet till höger, cirka 34 px
  radavstånd, ingen ram (referensen: "Name / Status / Owner" i grått, värdet i svart).
- **MetadataList props:** `children` (krävs), `title`, `columns`
  (`single | multi | number`), `label` (`{ position: "start" | "top", width }`),
  `orientation` (`vertical | horizontal`), `maxNumOfItems` (visa fler/färre).
- **MetadataListItem props:** `label` (krävs, **sträng**), `children` (krävs, värdet),
  `icon` (före etiketten).
- **Fällor:** grupper är flera `MetadataList` med var sin `title`. `label` på
  `MetadataListItem` kan inte vara JSX. Ett tomt värde måste du rendera själv (en
  `Button variant="ghost" size="sm"` med "Lägg till").

### Table och TableColumn

```tsx
import { Building2 } from "lucide-react";
import { HStack } from "@astryxdesign/core/Stack";
import { Icon } from "@astryxdesign/core/Icon";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import type { Bolag } from "@/lib/crm/api";

const kolumner: TableColumn<Bolag>[] = [
  {
    key: "name",
    header: (
      <HStack gap={1.5} vAlign="center">
        <Icon icon={Building2} size="sm" color="secondary" />
        Bolag
      </HStack>
    ),
    width: proportional(3, { minWidth: 200 }),
    renderCell: (b) => <Text weight="semibold">{b.name}</Text>
  },
  { key: "employees", header: "Anställda", width: pixel(110), align: "end", renderCell: (b) => <Text hasTabularNumbers>{b.employees ?? ""}</Text> }
];

export function Tabell({ rader }: { rader: Bolag[] }) {
  return <Table<Bolag> data={rader} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover />;
}
```

- **Ser ut:** rubrikrad i halvfet dämpad text, rader med hårlinje emellan (referensen:
  cirka 38 px rader i `balanced`, ingen yttre ram), hovringston på raden med `hasHover`.
- **Table props:** `data`, `columns`, `idKey` (egenskapsnamn eller funktion), `density`
  (`compact | balanced | spacious`), `dividers` (`rows | columns | grid | none`),
  `isStriped`, `hasHover`, `verticalAlign`, `textOverflow` (`wrap | truncate`),
  `plugins` (objekt: `{ selection, sort, … }`), `emptyState` (ReactNode eller `false`),
  `rowCount`, `virtualization`, `children` (eget läge), `className`, `style`.
- **TableColumn<T>:** `key` (krävs, sträng), `header?: ReactNode` (text eller JSX: ikon
  plus text fungerar), `width?: proportional(n, { minWidth }) | pixel(n)` (från
  `/Table`; **inte ett tal**), `align?: "start" | "center" | "end"` (gäller både rubrik
  och celler), `sortable?: true | { sortKey }`, `resizable?`, `filter?`,
  `renderCell?: (item: T) => ReactNode` (får **bara raden**: inget index, ingen
  kolumn). Utan `renderCell` visas `String(item[key])`.
- **Det som INTE finns:**
  - **Ingen `onRowClick`** och ingen klickbar rad. Öppna en post från en knapp eller
    länk i huvudcellens `renderCell` (postchipet).
  - **Ingen fot i dataläget.** `TableFooter`, `TableHeader`, `TableBody`, `TableRow`,
    `TableCell`, `TableHeaderCell` gäller bara `children`-läget, och `children` ersätter
    hela data-renderingen (då fungerar inte `columns` och tabellhookarna). Räknefoten
    och raden "Lägg till" ritas därför **under** `<Table>` (recept b).
  - Ingen inbyggd laddningsrad: rita `Skeleton` själv.
- **Fällor:**
  - Ange typen: `<Table<Bolag> …>` och `TableColumn<Bolag>[]`; den går inte alltid att
    härleda.
  - `useMemo` på `columns` om de byggs i komponenten; annars ritas alla celler om vid
    varje render.
  - `emptyState` visas bara när `data` är en tom lista (inte `undefined`).
  - Tabellen rullar i sidled när kolumnerna inte får plats. Kontraktet förbjuder det på
    mobil: under 640 px renderas en `List` i stället (se `List`).

### useTableSelectionState, useTableSelection och TableSelectionToolbar

```tsx
import { useState } from "react";
import { Button } from "@astryxdesign/core/Button";
import { Table, TableSelectionToolbar, useTableSelection, useTableSelectionState, type TableColumn } from "@astryxdesign/core/Table";
import type { Bolag } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

export function Markering({ rader, kolumner }: { rader: Bolag[]; kolumner: TableColumn<Bolag>[] }) {
  const { text } = useLocale();
  const [valda, setValda] = useState<Set<string>>(new Set());
  const { selectionConfig, selectionState } = useTableSelectionState<Bolag>({ data: rader, idKey: "id", selectedKeys: valda, setSelectedKeys: setValda });
  const markering = useTableSelection<Bolag>({ ...selectionConfig, getRowLabel: (b) => b.name ?? b.id });
  return (
    <>
      <TableSelectionToolbar
        selection={selectionState}
        label={text({ sv: "Åtgärder för markerade", en: "Bulk actions" })}
        renderSelectionLabel={(n) => text({ sv: `${n} markerade`, en: `${n} selected` })}
        clearLabel={text({ sv: "Avmarkera alla", en: "Unselect all" })}
        startContent={<Button label={text({ sv: "Ändra relation", en: "Change relation" })} variant="ghost" />}
      />
      <Table<Bolag> data={rader} columns={kolumner} idKey="id" plugins={{ selection: markering }} />
    </>
  );
}
```

- **Ser ut:** en kryssrutekolumn först, i rubriken en markera-alla-ruta (med
  mellanläge); markerade rader får en accenttonad bakgrund. Verktygsraden är en
  `Toolbar` i dämpad yta med dina knappar till vänster och "N markerade" plus
  "Avmarkera alla" till höger.
- **useTableSelectionState<T>(config):** `data`, `idKey` (egenskapsnamn eller
  `(item) => string`), `selectedKeys: Set<string>`, `setSelectedKeys` (alla krävs),
  `getIsItemSelectable`, `getIsItemEnabled`. Returnerar `{ selectionConfig,
  selectionState }` där `selectionState = { selectedKeys, selectedCount, hasSelection,
  clearSelection }`.
- **useTableSelection<T>(config):** tar `selectionConfig` och kan få `getRowLabel`
  (kryssrutans dolda namn: "Select <namn>") och `hasRowHighlight`.
- **TableSelectionToolbar props:** `selection` (krävs), `startContent` (dina åtgärder),
  `label`, `renderSelectionLabel(n)`, `clearLabel`, `size` (standard `sm`), `variant`
  (standard `muted`), plus Toolbar-props utom `endContent`.
- **Fällor:**
  - Verktygsraden **returnerar `null`** när inget är markerat. Ge den en plats som inte
    hoppar (ovanför tabellen i vyraden, eller flytande längst ned).
  - Plugin-nyckeln är valfri men objektet är ett **objekt**, inte en lista:
    `plugins={{ selection: markering }}`.
  - `selectedKeys` är nycklar som strängar; ett numeriskt id blir en sträng.
  - Markeringen överlever omfiltrering: rensa med `clearSelection()` när listan byts.
  - Standardtexterna är engelska: skicka alltid `renderSelectionLabel` och `clearLabel`.

### useTableSortable och useTableSortableState

```tsx
import { Table, useTableSortable, useTableSortableState, type TableColumn } from "@astryxdesign/core/Table";
import type { Bolag } from "@/lib/crm/api";

export function Sorterad({ rader, kolumner }: { rader: Bolag[]; kolumner: TableColumn<Bolag>[] }) {
  const { sortedData, sortConfig } = useTableSortableState<Bolag>({ data: rader, defaultSort: [{ sortKey: "name", direction: "ascending" }] });
  const sortering = useTableSortable<Bolag>(sortConfig);
  return <Table<Bolag> data={sortedData} columns={kolumner} idKey="id" plugins={{ sort: sortering }} />;
}
```

- **Ser ut:** sorterbara rubriker får en liten pil (upp, ned eller upp-ned).
- **useTableSortable<T>(config):** `sort` (lista av `{ sortKey, direction }`),
  `onSortChange` (båda krävs), `allowUnsortedState`, `isMultiSortEnabled`. Pluginet
  **sorterar inte raderna**; det ritar bara rubrikerna.
- **useTableSortableState<T>:** sorterar i minnet och ger `sortedData`, `sort`,
  `sortConfig`, `applySort`.
- **Fällor:** kolumnen måste ha `sortable: true`. Typargumentet måste skickas
  (`useTableSortable<Bolag>`). CRM:ets API sorterar på servern: använd då bara
  `useTableSortable` med egen `sort`-state och hämta om vid `onSortChange`, eller
  kontraktets "Sortera som ett kompakt val" (`Selector`) i vyraden.

### Pagination

```tsx
import { useState } from "react";
import { Pagination } from "@astryxdesign/core/Pagination";

export function Sidor({ antal }: { antal: number }) {
  const [sida, setSida] = useState(1);
  return <Pagination page={sida} onChange={setSida} totalItems={antal} pageSize={50} variant="count" />;
}
```

- **Props:** `page` (1-baserad) och `onChange` (krävs), `totalItems` eller `totalPages`
  eller `hasMore`, `pageSize` (standard 10), `pageSizeOptions`/`onPageSizeChange`,
  `variant` (`pages count compact dots input none`), `siblingCount`, `hasFirstLast`,
  `size` (`sm | md`), `label`, `getPageHref`/`as`.
- **Fälla:** CRM:ets API är markörbaserat (`next_cursor`); sidnummer går inte att hoppa
  till. Använd en "Visa fler"-knapp eller `hasMore` med `variant="compact"`.
  (`useTablePagination` finns som plugin men sköter klientsidesuppdelning.)

### List, ListItem och Item

```tsx
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Item } from "@astryxdesign/core/Item";
import { List, ListItem } from "@astryxdesign/core/List";

export function Mobillista({ oppna }: { oppna: () => void }) {
  return (
    <>
      <List hasDividers density="balanced">
        <ListItem
          label="Byggbolaget Norr"
          description="Umeå · Anna Lind"
          startContent={<Avatar name="Byggbolaget Norr" size="sm" shape="rounded" tooltip={false} />}
          endContent={<Badge variant="green" label="Kund" />}
          onClick={oppna}
        />
      </List>
      <Item label="Anna Lind" description="VD" startContent={<Avatar name="Anna Lind" size="xsm" />} density="compact" />
    </>
  );
}
```

- **Ser ut:** rader med startinnehåll, etikett och dämpad beskrivning, slutinnehåll till
  höger; klickbara rader får hovringsplatta.
- **List props:** `children`, `density` (`compact | balanced | spacious`), `hasDividers`,
  `edge` (`padded | flush | outset | bleed`), `header`, `listStyle`.
- **ListItem props:** `label` (krävs), `description` (en sträng kortas till en rad),
  `startContent`, `endContent`, `onClick` eller `href`, `isSelected`, `isDisabled`,
  `align`.
- **Item props:** som ListItem plus `as`, `layout` (`stacked | inline`), `labelLines`,
  `descriptionLines`, `isHighlighted`; ett fristående radprimitiv (menyer, kontaktrader).
- **Fälla:** ListItem med `onClick` blir en osynlig knapp över raden: lägg inte fler
  knappar i raden, då konkurrerar de.

### Timestamp

```tsx
import { Timestamp } from "@astryxdesign/core/Timestamp";

export function Andrad({ iso }: { iso: string }) {
  return <Timestamp value={iso} format="relative" />;
}
```

- **Ser ut:** dämpad text ("för 3 timmar sedan"); hovring eller fokus visar ett kort
  med fullständig tid som går att kopiera.
- **Props:** `value` (krävs: ISO-sträng eller **unix-sekunder**), `format` (`relative
  relative_short auto date date_long date_weekday date_time time system_date
  system_date_time system_time unix_seconds`; standard `auto` växlar från relativ till
  datum efter `autoThreshold` = 7 dygn), `hasTooltip` (standard `true`), `isLive`,
  `timezoneID`, `type`, `size`, `color` (standard `secondary`), `weight`.
- **Fällor:** `Date.now()` är millisekunder och blir ett datum långt fram: dela med 1000
  eller skicka ISO. Språket följer `InternationalizationProvider` i `CrmRam`.

---

## Kontroller

### Button

```tsx
import { Plus } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { Icon } from "@astryxdesign/core/Icon";
import { useLocale } from "@/lib/i18n";

export function Primar({ ny }: { ny: () => void }) {
  const { text } = useLocale();
  return (
    <Button
      label={text({ sv: "Nytt bolag", en: "New company" })}
      variant="primary"
      size="md"
      icon={<Icon icon={Plus} size="sm" />}
      onClick={ny}
    />
  );
}
```

- **Ser ut:** rundad knapp; `primary` fylld (bläck i Snajp), `secondary` ljusgrå platta
  (referensen: "Open Command Palette" på grå platta, radie cirka 10 px), `ghost` bara
  text med hovringsplatta, `destructive` i felfärg.
- **Props:** `label` (krävs, synlig text), `variant`, `size` (`sm | md | lg`), `icon`
  (före texten), `endContent` (en `Icon` eller `Badge`), `isIconOnly`, `isLoading`,
  `isDisabled`, `tooltip`, `onClick`, `clickAction` (async, visar laddning själv),
  `type`, `form`, `href`/`as`/`target`/`rel`, `width`, `elevation`.
- **Fällor:** ingen fullbredds-prop (lägg den i `VStack hAlign="stretch"` eller sätt
  `width="100%"`). `isDisabled` sätter `aria-disabled`, så knappen är fokuserbar och
  tooltip kan förklara varför.

### IconButton

```tsx
import { Mail } from "lucide-react";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { useLocale } from "@/lib/i18n";

export function Mejla({ adress }: { adress: string | null }) {
  const { text } = useLocale();
  return (
    <IconButton
      label={text({ sv: "Mejla", en: "Email" })}
      icon={<Icon icon={Mail} />}
      variant="secondary"
      size="md"
      href={adress ? `mailto:${adress}` : undefined}
      isDisabled={!adress}
      tooltip={adress ? undefined : text({ sv: "E-post saknas", en: "No email" })}
    />
  );
}
```

- **Ser ut:** kvadratisk knapp med bara ikon (samma varianter som Button).
- **Props:** `label` (krävs, blir aria-label), `icon` (krävs), `variant` (standard
  `secondary`), `size`, `tooltip`, `isDisabled`, `isLoading`, `onClick`, `clickAction`,
  `href`, `width`, `elevation`.
- **Fällor:** runda snabbvalsknappar (kontraktet) får formen av temat eller en
  `className` med `rounded-full`; det finns ingen `shape`-prop. Utan `tooltip` visas
  `label` som tooltip.

### SegmentedControl och SegmentedControlItem

```tsx
import { useState } from "react";
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl";
import { useLocale } from "@/lib/i18n";

export function Vyval() {
  const { text } = useLocale();
  const [vy, setVy] = useState("alla");
  return (
    <SegmentedControl value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} size="md">
      <SegmentedControlItem value="alla" label={text({ sv: "Alla 73", en: "All 73" })} />
      <SegmentedControlItem value="kunder" label={text({ sv: "Kunder 46", en: "Customers 46" })} />
    </SegmentedControl>
  );
}
```

- **Ser ut:** en ljusgrå helt rundad skena; det valda segmentet är en vit platta med
  halvfet text som glider till nytt val (referensen: "Grid | List | Table").
- **SegmentedControl props:** `value`, `onChange(value: string)`, `label` (aria, syns
  inte), `children` (alla krävs), `size`, `layout` (`hug | fill`), `isDisabled`,
  `disabledMessage`.
- **SegmentedControlItem props:** `value`, `label` (krävs, **sträng**), `icon`,
  `isLabelHidden`, `isDisabled`.
- **Fällor:** `label` är en sträng och det finns ingen `endContent`: kontraktets "antal
  i dämpad ton" går inte att rendera i ett segment. Antingen står antalet i
  etikettsträngen (samma ton), eller så används `TabList` med `Tab endContent`.
  Skenan är halvgenomskinlig: kontrollera kontrasten på bladets bakgrund. Det är ett
  val av vy, inte navigering mellan sidor.

### TabList och Tab

```tsx
import { useState } from "react";
import { Badge } from "@astryxdesign/core/Badge";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { useLocale } from "@/lib/i18n";

export function Flikar({ personer }: { personer: number }) {
  const { text } = useLocale();
  const [flik, setFlik] = useState("oversikt");
  return (
    <TabList value={flik} onChange={setFlik} hasDivider>
      <Tab value="oversikt" label={text({ sv: "Översikt", en: "Overview" })} />
      <Tab value="personer" label={text({ sv: "Personer", en: "People" })} endContent={<Badge label={String(personer)} />} />
    </TabList>
  );
}
```

- **Ser ut:** en rad flikar med text och valfri ikon; den valda fliken är markerad
  (ingen referensbild kontrollerad för just TabList: se den i bild).
- **TabList props:** `value`, `onChange`, `children` (krävs), `size`, `layout`,
  `hasDivider`, `isFullBleed` (når förbi behållarens padding), `overflow`.
- **Tab props:** `value`, `label` (krävs, sträng), `icon`, `selectedIcon`,
  `endContent` (passivt), `isLabelHidden`, `href`/`as`, `panelId`.
- **Fälla:** TabList ritar inga panelinnehåll; rendera innehållet för `flik` själv.

### Toolbar

```tsx
import { Button } from "@astryxdesign/core/Button";
import { Toolbar } from "@astryxdesign/core/Toolbar";
import { useLocale } from "@/lib/i18n";

export function Verktyg() {
  const { text } = useLocale();
  return (
    <Toolbar
      label={text({ sv: "Tabellverktyg", en: "Table tools" })}
      startContent={<Button label={text({ sv: "Filter", en: "Filter" })} variant="ghost" size="sm" />}
      endContent={<Button label={text({ sv: "Sortera", en: "Sort" })} variant="ghost" size="sm" />}
      dividers={["bottom"]}
    />
  );
}
```

- **Props:** `label` (krävs), `startContent`, `centerContent`, `endContent`, `size`
  (styr höjden och ärvs av barnen), `gap` (standard 1), `orientation`, `variant`
  (Section-variant, standard `transparent`), `dividers`.
- **Fälla:** för åtgärder inom innehåll (tabell, kort, panel), inte som sidhuvud.
  `size` ärvs av barn som inte har egen `size`: knappar i en `Toolbar size="sm"` blir
  `sm` (32 px) om du inte skriver `size="md"` på dem.

### Tooltip

```tsx
import { Text } from "@astryxdesign/core/Text";
import { Tooltip } from "@astryxdesign/core/Tooltip";

export function Tid() {
  return (
    <Tooltip content="26 november 2026 14:03">
      <Text color="secondary">för 2 h sedan</Text>
    </Tooltip>
  );
}
```

- **Ser ut:** en liten bubbla med kort text ovanför utlösaren, efter 200 ms; ren text
  som utlösare får en streckad understrykning som tecken på att det finns mer.
- **Props:** `content`, `children` (utlösaren), `placement` (standard `above`),
  `alignment`, `delay` (200), `hideDelay`, `focusTrigger`, `touchTrigger`, `isEnabled`,
  `hasHoverIndication`, `isOpen`/`isDefaultOpen`/`onOpenChange`, `anchorRef`.
- **Fällor:** `Button`, `IconButton`, `StatusDot` och `Avatar` har egen `tooltip`-prop;
  linda dem inte. För tid: `Timestamp` har redan sitt kort.

### HoverCard

```tsx
import { HoverCard } from "@astryxdesign/core/HoverCard";
import { Text } from "@astryxdesign/core/Text";

export function Forhandsvisning() {
  return (
    <HoverCard label="Byggbolaget Norr" content={<Text>Kund sedan 2021 · Umeå</Text>} placement="below">
      <Text weight="semibold">Byggbolaget Norr</Text>
    </HoverCard>
  );
}
```

- **Ser ut:** ett vitt kort med skugga som visas efter 300 ms hovring eller fokus.
- **Props:** `content` (krävs), `children`, `placement`, `alignment`, `delay` (300),
  `hideDelay` (200), `label`, `focusTrigger`, `touchTrigger`, `isEnabled`,
  `hasHoverIndication`, `isOpen`/`onOpenChange`, `className`, `style` (på kortet).
- **Fälla:** bara för extra information; inget som måste gå att nå på pekskärm.

### Popover

```tsx
import { Button } from "@astryxdesign/core/Button";
import { Popover } from "@astryxdesign/core/Popover";
import { Text } from "@astryxdesign/core/Text";

export function Info() {
  return (
    <Popover label="Om synken" content={<Text>Synken körs var 15:e minut.</Text>} placement="below" alignment="end">
      <Button label="Om synken" variant="ghost" size="sm" />
    </Popover>
  );
}
```

- **Props:** `content` (krävs), `children` (utlösaren), `placement` (standard `below`),
  `alignment` (`start`), `isOpen`/`onOpenChange`, `width`, `padding` (standard 3),
  `label`, `role`, `isModal`, `hasLightDismiss`, `hasEscapeDismiss`, `hasAutoFocus`,
  `presentation` (`popover | bottom-sheet | adaptive`).
- **Fälla:** klickutlöst. För menyer med val, använd `DropdownMenu`.

### TextInput

```tsx
import { useState } from "react";
import { TextInput } from "@astryxdesign/core/TextInput";
import { useLocale } from "@/lib/i18n";

export function Sokfalt() {
  const { text } = useLocale();
  const [sok, setSok] = useState("");
  return (
    <TextInput
      type="search"
      label={text({ sv: "Sök bolag", en: "Search companies" })}
      isLabelHidden
      placeholder={text({ sv: "Sök", en: "Search" })}
      startIcon="search"
      hasClear
      value={sok}
      onChange={(v) => setSok(v)}
      width={260}
      controlClassName="rounded-full"
    />
  );
}
```

- **Props:** `label` och `value` (krävs), `onChange(value, event)`, `type` (`text
  password email search tel url`), `size`, `isLabelHidden`, `placeholder`,
  `description`, `startIcon`, `hasClear`, `status` (`{ type: "error" | "warning" |
  "success", message? }`), `statusVariant`, `isRequired`/`isOptional`, `isDisabled`,
  `isReadOnly`, `isLoading`, `onEnter`, `onKeyDown`, `htmlName`, `width`,
  `autoComplete`, `inputMode`, `containerClassName`/`controlClassName`
  (+ `…Style`).
- **Fällor:** `onChange` får **värdet först**, inte eventet. `value` är obligatorisk
  (alltid kontrollerad). Fältfel från API:t: `status={{ type: "error", message }}`.
  Rundningen sätts på kontrollboxen (`controlClassName`), inte på roten.

### Selector

```tsx
import { useState } from "react";
import { Selector } from "@astryxdesign/core/Selector";
import { useLocale } from "@/lib/i18n";

export function Relationsval() {
  const { text } = useLocale();
  const [varde, setVarde] = useState<string>("customer");
  return (
    <Selector
      label={text({ sv: "Relation", en: "Relation" })}
      value={varde}
      onChange={(v) => v && setVarde(v)}
      options={[
        { value: "customer", label: text({ sv: "Kund", en: "Customer" }) },
        { value: "prospect", label: text({ sv: "Prospekt", en: "Prospect" }) }
      ]}
    />
  );
}
```

- **Props:** `label` och `options` (krävs), `value`, `onChange(value | null)`,
  `placeholder`, `hasClear` (då är `value` krävd och `null` = inget val), `hasSearch`,
  `variant` (`input | secondary | ghost`; `ghost` passar "Sortera" i vyraden),
  `size`, `isLabelHidden`, `status`, `isRequired`, `isDisabled`, `startIcon`,
  `renderOption`, `renderValue`, `width`.
- **`options`:** strängar, `{ value, label, description?, icon?, disabled? }`,
  `{ type: "divider" }` eller `{ type: "section", title, options }`.
- **Fälla:** `onChange` kan få `null` (med `hasClear`); typa hanteraren därefter.

### Switch

```tsx
import { useState } from "react";
import { Switch } from "@astryxdesign/core/Switch";
import { useLocale } from "@/lib/i18n";

export function KontaktaInte() {
  const { text } = useLocale();
  const [pa, setPa] = useState(false);
  return <Switch label={text({ sv: "Kontakta inte", en: "Do not contact" })} value={pa} onChange={(v) => setPa(v)} />;
}
```

- **Props:** `label` och `value` (krävs), `onChange(checked, event)`, `changeAction`,
  `description`, `size` (`sm | md`), `labelPosition`, `labelSpacing`
  (`hug | spread`), `isDisabled`, `status`, `htmlName`.
- **Fälla:** för val som gäller direkt. I en redigeringsdialog som sparas med en knapp
  är `CheckboxInput` det rätta enligt Astryx.

### CheckboxInput

```tsx
import { useState } from "react";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { useLocale } from "@/lib/i18n";

export function Kryss() {
  const { text } = useLocale();
  const [v, setV] = useState(false);
  return <CheckboxInput label={text({ sv: "Kontakta inte", en: "Do not contact" })} value={v} onChange={(c) => setV(c)} />;
}
```

- **Props:** `label` och `value` (krävs; `boolean | "indeterminate"`),
  `onChange(checked, event)`, `description`, `isLabelHidden`, `size`, `isDisabled`,
  `isReadOnly`, `status` (`message` krävs här), `labelIcon`, `htmlName`.
- **Fälla:** tabellens kryssrutor kommer från `useTableSelection`; rita inga egna.

### DateInput

```tsx
import { useState } from "react";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { DateInput } from "@astryxdesign/core/DateInput";
import { useLocale } from "@/lib/i18n";

export function Avtalsslut({ fran }: { fran: string | null }) {
  const { text } = useLocale();
  // API:t ger en vanlig sträng; DateInput vill ha mallsträngstypen ISODateString.
  const [datum, setDatum] = useState<ISODateString | undefined>(
    fran && /^\d{4}-\d{2}-\d{2}$/.test(fran) ? (fran as ISODateString) : undefined
  );
  return (
    <DateInput
      label={text({ sv: "Avtalsslut", en: "Contract end" })}
      value={datum}
      onChange={setDatum}
      weekStartsOn="mon"
      format="date"
      hasClear
    />
  );
}
```

- **Props:** `label` (krävs), `value` (`"YYYY-MM-DD"`), `onChange(value | undefined)`,
  `min`, `max`, `weekStartsOn`, `format`, `hasClear`, `status`, `isRequired`,
  `isDisabled`, `presentation`, `size`, `width`, `onEntryErrorChange`.
- **Fällor:** **veckan börjar på söndag** som standard: skicka `weekStartsOn="mon"`.
  Värdet är typen `ISODateString` (en mallsträng `"YYYY-MM-DD"`, importeras från
  `@astryxdesign/core/Calendar`, inte från `/DateInput`), inte `Date` och inte `string`:
  `useState<string>` ger typfel. På pekskärm visas webbläsarens egen
  väljare (`presentation="adaptive-native"`).

---

## Återkoppling och tillstånd

### Skeleton

```tsx
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";

export function Laddrad({ index }: { index: number }) {
  return (
    <HStack gap={3} vAlign="center" style={{ height: 44 }}>
      <Skeleton width={24} height={24} radius={2} index={index} />
      <Skeleton width="40%" height={12} radius="rounded" index={index} />
    </HStack>
  );
}
```

- **Ser ut:** ljusgrå block med en svepande glans.
- **Props:** `width` och `height` (standard `100%`), `radius` (`none 0 1 2 3 4 rounded`,
  standard 3), `index` (förskjuter animationen).
- **Fälla:** fyller förälderns storlek om du inte sätter mått; i en rad utan höjd blir
  den osynlig.

### Spinner

```tsx
import { Spinner } from "@astryxdesign/core/Spinner";

export function Snurra() {
  return <Spinner size="sm" aria-label="Laddar" />;
}
```

- **Props:** `size` (`sm` 10, `md` 14, `lg` 18, `xl` 28 px), `shade`, `label` (synlig
  text under), `aria-label` (standard "Loading").
- **Fälla:** kontraktet vill ha `Skeleton` i tabellen; spinnern är för knappar och
  okänd form.

### ProgressBar

```tsx
import { ProgressBar } from "@astryxdesign/core/ProgressBar";

export function Forlopp({ klart, totalt }: { klart: number; totalt: number }) {
  return <ProgressBar label="Synk" isLabelHidden value={klart} max={totalt} variant="accent" />;
}
```

- **Ser ut:** tunn rundad stapel; fyllnaden i accent (ockra).
- **Props:** `label` (krävs), `value`, `max` (100), `isLabelHidden`, `hasValueLabel`,
  `formatValueLabel`, `variant` (`accent success warning error neutral`),
  `isIndeterminate`, `marks`, `isDisabled`.
- **Fälla:** `isIndeterminate` när det totala inte är känt (kö), annars värdet.

### EmptyState

```tsx
import { Building2 } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { useLocale } from "@/lib/i18n";

export function Tomt({ ny }: { ny: () => void }) {
  const { text } = useLocale();
  return (
    <EmptyState
      icon={<Icon icon={Building2} size="lg" color="secondary" />}
      title={text({ sv: "Inga bolag än", en: "No companies yet" })}
      description={text({ sv: "Lägg till det första eller koppla en synk.", en: "Add the first one or connect a sync." })}
      actions={<Button label={text({ sv: "Nytt bolag", en: "New company" })} variant="primary" onClick={ny} />}
    />
  );
}
```

- **Ser ut:** centrerad halvfet rubrik med dämpad text under (referensen: "No results
  found"), ikonen ovanför, knapparna under.
- **Props:** `title` (krävs), `description` (sträng), `icon` (dekorativ), `actions`,
  `headingLevel` (bara taggen), `isCompact`.
- **Fälla:** skicka den som `emptyState` till `Table` så hamnar den inne i tabellen.

### Banner

```tsx
import { Banner } from "@astryxdesign/core/Banner";

export function Synkfel() {
  return <Banner status="error" title="Synken misslyckades" description="Fortnox svarade inte." container="card" />;
}
```

- **Props:** `status` och `title` (krävs), `description`, `icon`, `endContent`,
  `isDismissable`/`onDismiss`/`dismissLabel`, `container` (`card | section`),
  `elevation`, `children`, `collapsible` (standard `true`: barnen ligger bakom en knapp).
- **Fälla:** `children` döljs bakom en växlare om du inte sätter `collapsible={false}`.

### Toast och useToast

```tsx
import { Button } from "@astryxdesign/core/Button";
import { useToast } from "@astryxdesign/core/Toast";
import { useLocale } from "@/lib/i18n";

export function Spara() {
  const { text } = useLocale();
  const visa = useToast();
  return (
    <Button
      label={text({ sv: "Spara", en: "Save" })}
      onClick={() => visa({ body: text({ sv: "Sparat", en: "Saved" }), uniqueID: "spara" })}
    />
  );
}
```

- **Ser ut:** ett litet kort som glider in vid skärmkanten och försvinner efter 5 s
  (`error` har felfärg och stannar tills det stängs).
- **useToast():** returnerar **funktionen** själv (inte ett objekt). Den tar `{ body,
  type?: "info" | "error", isAutoHide?, autoHideDuration?, endContent?, uniqueID?,
  collisionBehavior?, onHide?, renderContent? }` och returnerar en stängfunktion.
- **Fällor:** ingen provider krävs, men utan `ToastViewport`/`LayerProvider` monteras en
  reserv på `document.body` med en varning i utvecklingsläge. Kalla inte `useToast` i
  samma komponent som renderar providern. Fel som kräver beslut: `AlertDialog`, inte
  toast. `<Toast>` som komponent är för förhandsvisningar.

---

## Overlägg

### Drawer och DrawerHeader

```tsx
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { Layout, LayoutContent } from "@astryxdesign/core/Layout";

export function Panel({ oppen, setOppen }: { oppen: boolean; setOppen: (o: boolean) => void }) {
  return (
    <Drawer isOpen={oppen} onOpenChange={setOppen} label="Byggbolaget Norr" width={520}>
      <Layout header={<DrawerHeader title="Byggbolaget Norr" onOpenChange={setOppen} />} content={<LayoutContent>…</LayoutContent>} />
    </Drawer>
  );
}
```

- **Ser ut:** helhöjdspanel från höger över en dämpning; under 640 px lämnar den 56 px
  av sidan synlig.
- **Drawer props:** `isOpen`, `onOpenChange`, `label`, `children` (krävs), `side`
  (`end` = höger), `width` (standard 400), `hasScrim`, `purpose` (`info` = Esc och klick
  utanför stänger, `form` = bara Esc, `required` = ingetdera), `padding`.
- **DrawerHeader props:** `title` (krävs, renderas som h2), `subtitle`, `onOpenChange`
  (ger stängknappen; utan den ingen knapp), `startContent`, `endContent`, `hasDivider`.
- **Fällor:** Drawer har **ingen inbyggd stängknapp**: skicka `onOpenChange` till
  `DrawerHeader` eller rita en egen. Nästla aldrig lådor. `data-autofocus` på ett element
  väljer fokus vid öppning.

### Dialog och DialogHeader

```tsx
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { HStack } from "@astryxdesign/core/Stack";

export function Redigera({ oppen, setOppen }: { oppen: boolean; setOppen: (o: boolean) => void }) {
  return (
    <Dialog isOpen={oppen} onOpenChange={setOppen} width={560} purpose="form">
      <Layout
        header={<DialogHeader title="Redigera bolag" onOpenChange={setOppen} />}
        content={<LayoutContent>…</LayoutContent>}
        footer={
          <LayoutFooter>
            <HStack gap={2} hAlign="end">
              <Button label="Avbryt" variant="ghost" onClick={() => setOppen(false)} />
              <Button label="Spara" variant="primary" type="submit" form="redigera-bolag" />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
```

- **Props:** `isOpen`, `onOpenChange`, `children` (krävs), `width` (400), `maxHeight`
  (`75dvh`), `variant` (`standard | fullscreen`), `purpose`, `padding`, `position`.
- **DialogHeader:** `title`, `subtitle`, `onOpenChange` (stängknapp), `startContent`,
  `endContent`, `hasDivider` (standard `true`).
- **Fällor:** titeln fokuseras vid öppning och namnger dialogen. Formulär: lägg
  `<form id="…">` i innehållet och `form="…"` på sparaknappen i foten.

### AlertDialog

```tsx
import { AlertDialog } from "@astryxdesign/core/AlertDialog";

export function TaBort({ oppen, setOppen, taBort }: { oppen: boolean; setOppen: (o: boolean) => void; taBort: () => void }) {
  return (
    <AlertDialog
      isOpen={oppen}
      onOpenChange={setOppen}
      title="Ta bort 3 bolag?"
      description="De flyttas till papperskorgen."
      actionLabel="Ta bort"
      cancelLabel="Avbryt"
      onAction={taBort}
    />
  );
}
```

- **Props:** `isOpen`, `onOpenChange`, `title`, `description`, `actionLabel`, `onAction`
  (alla krävs), `cancelLabel` (standard "Cancel"), `actionVariant` (standard
  `destructive`), `isActionLoading`, `width`.
- **Fällor:** `onAction` stänger inte dialogen: sätt `setOppen(false)` själv efter
  åtgärden. Utan dialogstate: `useImperativeAlertDialog()` ger `{ show(options), hide,
  isOpen, element }`; rendera `element`. `cancelLabel` måste skickas, annars engelska.

---

## Text och ikon

### Text och Heading

```tsx
import { Heading } from "@astryxdesign/core/Heading";
import { Text } from "@astryxdesign/core/Text";

export function Typografi() {
  return (
    <>
      <Heading level={1}>Bolag</Heading>
      <Text type="display-2" hasTabularNumbers>73</Text>
      <Text type="supporting" color="secondary">46 av 73 är kunder</Text>
    </>
  );
}
```

- **Text props:** `children` (krävs), `type` (`body large label supporting code
  display-1 display-2 display-3 inherit`), `size` (`4xs … 4xl`), `color` (`primary
  secondary disabled placeholder accent inherit`), `weight` (`normal medium semibold
  bold`), `display`, `as` (`span p div label h1 h2 h3`), `maxLines`,
  `hasTruncateTooltip`, `hasTabularNumbers`, `textWrap`, `justify`.
- **Heading props:** `level` (krävs, 1–6, styr både tagg och storlek), `type`
  (`display-1/2/3` byter bara utseendet), `accessibilityLevel`, `weight`, `color`,
  `maxLines`, `className`, `style`.
- **Fällor:** `Heading` använder temats rubriktypsnitt (`--font-family-heading` =
  Fraunces i `snajpTema.ts`); `Text type="display-*"` är en brödtexttyp och kan få
  Geist. Kontrollera i bild. Behövs Fraunces i ett nyckeltal: `className="font-display"`
  (Snajps Tailwind-klass för `--font-fraunces`). **Inte `font-serif`**: den är
  Tailwinds standard (ui-serif, Georgia) eftersom Snajp bara lägger till `display`,
  `sans` och `mono`. `color="accent"` blir ockra som text: kontraktet kräver
  `--warning` för ockra text.

### Icon

```tsx
import { Building2 } from "lucide-react";
import { Icon } from "@astryxdesign/core/Icon";

export function Ikon() {
  return (
    <>
      <Icon icon={Building2} size="sm" color="secondary" />
      <Icon icon="search" size="sm" />
      <Icon icon={Building2} size="md" label="Bolag" />
    </>
  );
}
```

- **Props:** `icon` (krävs: lucide-komponenten som värde, `icon={Building2}`, eller ett
  semantiskt namn), `size` (`xsm` 12, `sm` 16, `md` 20, `lg` 24 px), `color`
  (`primary secondary tertiary disabled accent info success error warning inherit blue
  red green gray cyan teal yellow orange pink purple`; standard `inherit`), `label`
  (gör ikonen meningsbärande), `variant`, `className`, `style`.
- **Fällor:** skicka komponenten, inte `<Building2 />`, till `Icon`. I `icon`-props på
  andra komponenter går båda. Utan `label` är ikonen dekorativ (aria-hidden). Färgen
  på en objektikonplatta (14 % alfa) är en `span` med `className`, inte en Icon-prop.

---

## Recept

Fem fullständiga komponenter enligt kontraktet. Varje recept är en egen fil som
typkontrollerats med repots `tsconfig`-inställningar (strict) mot 0.7.17; recept a
importerar recept c från `./recept-c`, så lägg dem bredvid varandra eller ändra vägen.
Data kommer från `lib/crm/api.ts` (`crmAnrop`, `Bolag`, `Oversikt`, `Korning`); inget
tal är påhittat. Recepten är byggstenar, inte färdiga vyer: tillstånd för hämtning,
dialoger och URL ligger i vyn som använder dem.

### a. Skalet

Fil: `recept-a.tsx`.

`AppShell variant="elevated"` med ljus sidnavigering: arbetsyteväxlare (rundad
fyrkantig avatar, namnet, vinkel, meny med Till arbetsytan och Inställningar) och en
sökknapp till höger, raden "Sök eller hoppa till" med `Kbd`, sektionerna Arbetsyta och
Data, och nederst ett litet kort med senaste synken (statusprick, anslutning, relativ
tid, förloppsstapel när en körning pågår) och länken Till arbetsytan.

Att tänka på:
- Avatarens bläckplatta kräver CSS:
  `.crm-arbetsyta .astryx-avatar-fallback { background-color: oklch(var(--ink)); color: oklch(var(--paper)); }`.
- Sökknappen i rubriken anropar `e.stopPropagation()`; annars öppnar klicket menyn också.
- Bredden 248 px är temats sidnavigeringsbredd; det finns ingen bredd-prop.
- `isSelected` räknas ut från `usePathname()`; Astryx gör det inte själv.
- Under brytpunkten `md` bygger AppShell själv mobilens toppremsa och låda av samma
  `SideNav`.

```tsx
"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { ArrowLeft, Building2, Code2, LayoutDashboard, RefreshCw, Search, Settings, Users } from "lucide-react";
import { AppShell } from "@astryxdesign/core/AppShell";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Card } from "@astryxdesign/core/Card";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Kbd } from "@astryxdesign/core/Kbd";
import { NavHeadingMenu, NavHeadingMenuItem } from "@astryxdesign/core/NavMenu";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { SideNav, SideNavHeading, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
import { HStack, StackItem, VStack } from "@astryxdesign/core/Stack";
import { StatusDot } from "@astryxdesign/core/StatusDot";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import type { Korning } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";
import { KommandoPalett } from "./recept-c";

type Vy = "oversikt" | "bolag" | "personer" | "synk" | "utvecklare";

/** Senaste synkens läge, längst ned i navigeringen. Riktiga data ur /oversikt. */
function SynkKort({ korning, anslutning }: Readonly<{ korning: Korning | null; anslutning: string | null }>) {
  const { text } = useLocale();
  if (!korning) return null;
  const pagar = korning.status === "queued" || korning.status === "processing";
  const lage =
    korning.status === "failed"
      ? { variant: "error" as const, text: text({ sv: "Misslyckades", en: "Failed" }) }
      : pagar
        ? { variant: "accent" as const, text: text({ sv: "Pågår", en: "Running" }) }
        : { variant: "success" as const, text: text({ sv: "Klar", en: "Done" }) };
  const tid = korning.completed_at ?? korning.created_at;
  return (
    <Card padding={3}>
      <VStack gap={2}>
        <HStack gap={2} vAlign="center">
          <StatusDot variant={lage.variant} label={lage.text} isPulsing={pagar} />
          <StackItem size="fill">
            <Text weight="semibold" maxLines={1}>
              {anslutning ?? text({ sv: "Synk", en: "Sync" })}
            </Text>
          </StackItem>
          {tid ? <Timestamp value={tid} format="relative_short" /> : null}
        </HStack>
        <Text type="supporting" color="secondary">
          {lage.text}
        </Text>
        {pagar ? (
          <ProgressBar
            label={text({ sv: "Synkens förlopp", en: "Sync progress" })}
            isLabelHidden
            isIndeterminate={korning.status === "queued" || korning.counts.total === 0}
            value={korning.counts.created + korning.counts.updated + korning.counts.unchanged + korning.counts.skipped}
            max={Math.max(korning.counts.total, 1)}
          />
        ) : null}
      </VStack>
    </Card>
  );
}

export function CrmSkal({
  arbetsyta,
  bas = "/crm",
  senaste,
  anslutning,
  oppnaBolag,
  skapa,
  children
}: Readonly<{
  arbetsyta: string;
  bas?: string;
  senaste: Korning | null;
  anslutning: string | null;
  oppnaBolag: (id: string) => void;
  skapa: (vad: "bolag" | "anslutning" | "nyckel") => void;
  children: React.ReactNode;
}>) {
  const { text } = useLocale();
  const vag = usePathname() ?? "";
  const aktiv: Vy = ((vag.startsWith(bas) ? vag.slice(bas.length).split("/")[1] : "") || "oversikt") as Vy;
  const [palett, setPalett] = useState(false);

  const post = (vy: Vy, sv: string, en: string, ikon: typeof Building2) => (
    <SideNavItem
      label={text({ sv, en })}
      href={vy === "oversikt" ? bas : `${bas}/${vy}`}
      icon={ikon}
      isSelected={aktiv === vy}
    />
  );

  return (
    <AppShell
      variant="elevated"
      contentPadding={0}
      mobileNav={{ breakpoint: "md" }}
      sideNav={
        <SideNav
          collapsible
          header={
            <SideNavHeading
              heading={arbetsyta}
              icon={<Avatar name={arbetsyta} size={24} shape="rounded" tooltip={false} className="crm-arbetsyta" />}
              menu={
                <NavHeadingMenu>
                  <NavHeadingMenuItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
                  <NavHeadingMenuItem label={text({ sv: "Inställningar", en: "Settings" })} href="/dashboard/installningar" icon={Settings} />
                </NavHeadingMenu>
              }
              headerEndContent={
                <IconButton
                  label={text({ sv: "Öppna kommandopaletten", en: "Open command palette" })}
                  icon={<Icon icon={Search} size="sm" />}
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    // Utan detta bubblar klicket till rubriken och öppnar menyn också.
                    e.stopPropagation();
                    setPalett(true);
                  }}
                />
              }
            />
          }
          topContent={
            <SideNavItem
              label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
              icon="search"
              onClick={() => setPalett(true)}
              endContent={<Kbd keys="mod+k" />}
            />
          }
          footer={
            <VStack gap={2}>
              <SynkKort korning={senaste} anslutning={anslutning} />
              <SideNavItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
            </VStack>
          }
        >
          <SideNavSection title={text({ sv: "Arbetsyta", en: "Workspace" })}>
            {post("oversikt", "Översikt", "Overview", LayoutDashboard)}
            {post("bolag", "Bolag", "Companies", Building2)}
            {post("personer", "Personer", "People", Users)}
          </SideNavSection>
          <SideNavSection title={text({ sv: "Data", en: "Data" })}>
            {post("synk", "Synk", "Sync", RefreshCw)}
            {post("utvecklare", "Utvecklare", "Developers", Code2)}
          </SideNavSection>
        </SideNav>
      }
    >
      {children}
      <KommandoPalett oppen={palett} setOppen={setPalett} bas={bas} oppnaBolag={oppnaBolag} skapa={skapa} />
    </AppShell>
  );
}
```

### b. Tabell med markering, verktygsrad, räknefot och ikonrubriker

Fil: `recept-b.tsx`.

Bolagstabellen: kryssruta per rad och i huvudet, `TableSelectionToolbar` med
kontraktets två åtgärder, kolumnrubriker med ikon, postchip i första kolumnen (hela
chipet är en knapp som öppnar panelen), länkpiller, relation som etikett med
statusprick, ansvarig med avatar, relativ tid. Under tabellen raden "Lägg till bolag"
och räknefoten. Medan första sidan laddar: skelettrader i tabellens form.

Att tänka på:
- `Table` har ingen `onRowClick`; chipet är det klickbara.
- Dataläget har ingen `tfoot`: "Lägg till" och foten är vanliga element under tabellen.
  Vill du att de rullar i sidled med tabellen går de att lägga i ett eget plugin
  (`{ transformScrollWrapper: (p) => ({ ...p, afterTable: <Fot /> }) }`, typen
  `TablePlugin<Bolag>`); det är inte provat i bild.
- Verktygsraden försvinner (returnerar `null`) när inget är markerat.
- `oppna` ska vara stabil (`useCallback`), annars byggs kolumnerna om varje render.
- Under 640 px: rendera `List`/`ListItem` i stället för `Table` (kontraktet).

```tsx
"use client";

import { useMemo, useState } from "react";
import { Building2, Clock, Globe, Mail, MapPin, Plus, Tag, UserRound } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { StatusDot } from "@astryxdesign/core/StatusDot";
import {
  Table,
  TableSelectionToolbar,
  pixel,
  proportional,
  useTableSelection,
  useTableSelectionState,
  type TableColumn
} from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Token } from "@astryxdesign/core/Token";
import { RELATIONER, type Bolag, type Relation } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Kontraktets relationsfärger. StatusDot har bara fem varianter; Badge bär färgen. */
const RELATIONSTIL: Record<Relation, { badge: "green" | "yellow" | "neutral" | "blue"; prick: "success" | "warning" | "neutral" | "accent" }> = {
  customer: { badge: "green", prick: "success" },
  prospect: { badge: "yellow", prick: "warning" },
  former_customer: { badge: "neutral", prick: "neutral" },
  partner: { badge: "blue", prick: "accent" },
  supplier: { badge: "blue", prick: "accent" },
  other: { badge: "neutral", prick: "neutral" }
};

/** Kolumnrubrik: liten dämpad ikon plus text, som Twentys. */
function Rubrik({ ikon, children }: Readonly<{ ikon: typeof Building2; children: string }>) {
  return (
    <HStack gap={1.5} vAlign="center">
      <Icon icon={ikon} size="sm" color="secondary" />
      {children}
    </HStack>
  );
}

/** Postchip: hela chipet är en knapp som öppnar panelen. Tabellen har ingen onRowClick. */
function Postchip({ bolag, oppna }: Readonly<{ bolag: Bolag; oppna: (b: Bolag) => void }>) {
  const { text } = useLocale();
  const namn = bolag.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });
  return (
    <button
      type="button"
      onClick={() => oppna(bolag)}
      className="inline-flex max-w-full items-center gap-2 rounded-md px-1 py-0.5 text-left peka:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[oklch(var(--ochre))]"
    >
      <Avatar name={namn.replace(/\s+AB$/i, "")} size={20} shape="rounded" tooltip={false} />
      <Text weight="semibold" maxLines={1}>
        {namn}
      </Text>
    </button>
  );
}

export function BolagTabell({
  rader,
  laddar,
  oppna,
  nytt,
  andraRelation,
  taBort
}: Readonly<{
  rader: Bolag[];
  laddar: boolean;
  oppna: (b: Bolag) => void;
  nytt: () => void;
  andraRelation: (ids: string[]) => void;
  taBort: (ids: string[]) => void;
}>) {
  const { text } = useLocale();
  const [valda, setValda] = useState<Set<string>>(new Set());
  const { selectionConfig, selectionState } = useTableSelectionState<Bolag>({
    data: rader,
    idKey: "id",
    selectedKeys: valda,
    setSelectedKeys: setValda
  });
  const markering = useTableSelection<Bolag>({
    ...selectionConfig,
    getRowLabel: (b) => b.name ?? b.id
  });

  const kolumner = useMemo<TableColumn<Bolag>[]>(
    () => [
      {
        key: "name",
        header: <Rubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Rubrik>,
        width: proportional(3, { minWidth: 220 }),
        renderCell: (b) => <Postchip bolag={b} oppna={oppna} />
      },
      {
        key: "domain",
        header: <Rubrik ikon={Globe}>{text({ sv: "Webbplats", en: "Website" })}</Rubrik>,
        width: proportional(2, { minWidth: 160 }),
        renderCell: (b) => (b.domain ? <Token label={b.domain} icon={<Icon icon={Globe} size="sm" />} size="sm" href={`https://${b.domain}`} /> : null)
      },
      {
        key: "email",
        header: <Rubrik ikon={Mail}>{text({ sv: "E-post", en: "Email" })}</Rubrik>,
        width: proportional(2, { minWidth: 180 }),
        renderCell: (b) => (b.email ? <Token label={b.email} icon={<Icon icon={Mail} size="sm" />} size="sm" href={`mailto:${b.email}`} /> : null)
      },
      {
        key: "relation",
        header: <Rubrik ikon={Tag}>{text({ sv: "Relation", en: "Relation" })}</Rubrik>,
        width: pixel(150),
        renderCell: (b) => {
          const namn = text(RELATIONER[b.relation]);
          const stil = RELATIONSTIL[b.relation];
          return <Badge variant={stil.badge} label={namn} icon={<StatusDot variant={stil.prick} label={namn} />} />;
        }
      },
      {
        key: "city",
        header: <Rubrik ikon={MapPin}>{text({ sv: "Ort", en: "City" })}</Rubrik>,
        width: proportional(1.5, { minWidth: 110 }),
        renderCell: (b) => b.address.city ?? ""
      },
      {
        key: "owner",
        header: <Rubrik ikon={UserRound}>{text({ sv: "Ansvarig", en: "Owner" })}</Rubrik>,
        width: proportional(1.5, { minWidth: 130 }),
        renderCell: (b) =>
          b.owner ? (
            <HStack gap={1.5} vAlign="center">
              <Avatar name={b.owner} size={20} tooltip={false} />
              <Text maxLines={1}>{b.owner}</Text>
            </HStack>
          ) : null
      },
      {
        key: "updated_at",
        header: <Rubrik ikon={Clock}>{text({ sv: "Ändrad", en: "Updated" })}</Rubrik>,
        width: pixel(130),
        align: "end",
        // Timestamp har redan ett kort med fullständig tid vid hovring.
        renderCell: (b) => (b.updated_at ? <Timestamp value={b.updated_at} format="relative" /> : null)
      }
    ],
    [text, oppna]
  );

  const kunder = rader.filter((b) => b.relation === "customer").length;
  const andel = rader.length ? Math.round((kunder / rader.length) * 100) : 0;

  if (laddar && rader.length === 0) {
    // Skelettrader i tabellens form, inte en naken förloppsstapel.
    return (
      <div aria-busy="true" className="divide-y divide-ink/10">
        {Array.from({ length: 8 }, (_, i) => (
          <HStack key={i} gap={3} vAlign="center" paddingInline={4} style={{ height: 44 }}>
            <Skeleton width={16} height={16} radius={1} index={i} />
            <Skeleton width={20} height={20} radius={2} index={i} />
            <Skeleton width="28%" height={12} radius="rounded" index={i} />
            <Skeleton width="18%" height={12} radius="rounded" index={i} />
            <Skeleton width="12%" height={12} radius="rounded" index={i} />
          </HStack>
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Returnerar null utan markering. Platsen ovanför tabellen hoppar då; lägg den
          i vyraden eller flytande om det stör. */}
      <TableSelectionToolbar
        selection={selectionState}
        label={text({ sv: "Åtgärder för markerade bolag", en: "Bulk actions for companies" })}
        renderSelectionLabel={(n) => text({ sv: `${n} markerade`, en: `${n} selected` })}
        clearLabel={text({ sv: "Avmarkera alla", en: "Unselect all" })}
        startContent={
          <>
            <Button
              label={text({ sv: "Ändra relation", en: "Change relation" })}
              variant="ghost"
              onClick={() => andraRelation([...selectionState.selectedKeys])}
            />
            <Button
              label={text({ sv: "Ta bort till papperskorgen", en: "Move to trash" })}
              variant="ghost"
              onClick={() => taBort([...selectionState.selectedKeys])}
            />
          </>
        }
      />
      <Table<Bolag>
        data={rader}
        columns={kolumner}
        idKey="id"
        density="balanced"
        dividers="rows"
        hasHover
        textOverflow="truncate"
        plugins={{ selection: markering }}
        emptyState={
          <EmptyState
            icon={<Icon icon={Building2} size="lg" color="secondary" />}
            title={text({ sv: "Inga bolag här", en: "No companies here" })}
            description={text({ sv: "Lägg till ett bolag eller koppla en synk.", en: "Add a company or connect a sync." })}
            actions={<Button label={text({ sv: "Nytt bolag", en: "New company" })} variant="primary" onClick={nytt} />}
          />
        }
      />
      {/* Dataläget har ingen tfoot: sista raden och räknefoten ritas under tabellen. */}
      {rader.length > 0 ? (
        <>
          <button
            type="button"
            onClick={nytt}
            className="flex h-11 w-full items-center gap-2 border-b border-ink/10 px-4 text-left text-ink-muted peka:bg-ink/5"
          >
            <Icon icon={Plus} size="sm" />
            <Text color="secondary">{text({ sv: "Lägg till bolag", en: "Add company" })}</Text>
          </button>
          <HStack gap={4} vAlign="center" paddingInline={4} style={{ height: 40 }}>
            <Text type="supporting" color="secondary" hasTabularNumbers>
              {text({ sv: `${rader.length} bolag`, en: `${rader.length} companies` })}
            </Text>
            <Text type="supporting" color="secondary" hasTabularNumbers>
              {text({ sv: `${andel} % kunder`, en: `${andel}% customers` })}
            </Text>
          </HStack>
        </>
      ) : null}
    </div>
  );
}
```

### c. Kommandopaletten med Ctrl K, grupper och asynkrona träffar

Fil: `recept-c.tsx`.

Gå till (fem vyer) och Skapa (tre val) som fasta kommandon, Bolag som sökning mot
`/v1/companies?q=` medan man skriver. Grupperna kommer av `auxiliaryData.group`.
Källan väntar 200 ms och avbryter förra anropet (`cancel()` anropas av paletten före
varje ny sökning). Val går genom `onValueChange` och paletten stänger sig själv.

Att tänka på:
- Paletten skickar ingen `context` till `search()`, så delresultat (`context.update`)
  fungerar inte här; returnera hela listan.
- `id` är prefixat per grupp så att ett bolags uuid aldrig krockar med ett kommando.
- `renderItem` returnerar bara passivt innehåll.
- Både `mod+k` och `ctrl+k` med `allowInInputs: true`, annars fungerar genvägen inte
  i sökfält.

```tsx
"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Building2, Code2, KeyRound, LayoutDashboard, Plus, RefreshCw, Users } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { CommandPalette, CommandPaletteInput } from "@astryxdesign/core/CommandPalette";
import { useHotkeys } from "@astryxdesign/core/hooks";
import { Icon } from "@astryxdesign/core/Icon";
import { HStack, StackItem } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import type { SearchSource, SearchableItem } from "@astryxdesign/core/Typeahead";
import { crmAnrop, type Bolag, type Sida } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Varje träff bär sin grupp och vad ett val ska göra. */
type Traff = SearchableItem<{
  group: string;
  slag: "ga" | "skapa" | "bolag";
  mal: string;
  ikon?: typeof Building2;
  ort?: string | null;
}>;

/** Bolagsnamn utan bolagsform, så att avatarens initialer blir rätt. */
function utanBolagsform(namn: string) {
  return namn.replace(/\s+(AB|HB|KB|Ek\.?\s*för\.?)$/i, "");
}

export function KommandoPalett({
  oppen,
  setOppen,
  bas = "/crm",
  oppnaBolag,
  skapa
}: Readonly<{
  oppen: boolean;
  setOppen: (oppen: boolean) => void;
  bas?: string;
  oppnaBolag: (id: string) => void;
  skapa: (vad: "bolag" | "anslutning" | "nyckel") => void;
}>) {
  const { text } = useLocale();
  const router = useRouter();

  // Ctrl K överallt och Cmd K på Mac. Den första träffen vinner, så inget körs två gånger.
  useHotkeys([
    { keys: "mod+k", onPress: () => setOppen(!oppen), allowInInputs: true },
    { keys: "ctrl+k", onPress: () => setOppen(!oppen), allowInInputs: true }
  ]);

  const kommandon = useMemo<Traff[]>(() => {
    const ga = text({ sv: "Gå till", en: "Go to" });
    const ny = text({ sv: "Skapa", en: "Create" });
    return [
      { id: "ga:oversikt", label: text({ sv: "Översikt", en: "Overview" }), auxiliaryData: { group: ga, slag: "ga", mal: `${bas}`, ikon: LayoutDashboard } },
      { id: "ga:bolag", label: text({ sv: "Bolag", en: "Companies" }), auxiliaryData: { group: ga, slag: "ga", mal: `${bas}/bolag`, ikon: Building2 } },
      { id: "ga:personer", label: text({ sv: "Personer", en: "People" }), auxiliaryData: { group: ga, slag: "ga", mal: `${bas}/personer`, ikon: Users } },
      { id: "ga:synk", label: text({ sv: "Synk", en: "Sync" }), auxiliaryData: { group: ga, slag: "ga", mal: `${bas}/synk`, ikon: RefreshCw } },
      { id: "ga:utvecklare", label: text({ sv: "Utvecklare", en: "Developers" }), auxiliaryData: { group: ga, slag: "ga", mal: `${bas}/utvecklare`, ikon: Code2 } },
      { id: "skapa:bolag", label: text({ sv: "Nytt bolag", en: "New company" }), auxiliaryData: { group: ny, slag: "skapa", mal: "bolag", ikon: Plus } },
      { id: "skapa:anslutning", label: text({ sv: "Ny anslutning", en: "New connection" }), auxiliaryData: { group: ny, slag: "skapa", mal: "anslutning", ikon: RefreshCw } },
      { id: "skapa:nyckel", label: text({ sv: "Ny nyckel", en: "New key" }), auxiliaryData: { group: ny, slag: "skapa", mal: "nyckel", ikon: KeyRound } }
    ];
  }, [text, bas]);

  // Stabil källa: en ny källa medan paletten är öppen kör om sökningen.
  const kalla = useMemo<SearchSource<Traff>>(() => {
    let styrning: AbortController | null = null;
    const bolagsgrupp = text({ sv: "Bolag", en: "Companies" });
    return {
      bootstrap: () => kommandon,
      // Paletten anropar cancel() före varje ny sökning och när den stängs.
      cancel: () => styrning?.abort(),
      async search(fraga) {
        const q = fraga.trim().toLowerCase();
        const lokala = kommandon.filter((k) => k.label.toLowerCase().includes(q));
        if (q.length < 2) return lokala;
        const denna = new AbortController();
        styrning = denna;
        // Paletten debouncar inte: vänta själv, och ge upp om nästa tangent hann före.
        await new Promise((klar) => window.setTimeout(klar, 200));
        if (denna.signal.aborted) return lokala;
        try {
          const sida = await crmAnrop<Sida<Bolag>>(
            `/v1/companies?${new URLSearchParams({ q: fraga.trim(), limit: "8" })}`,
            { signal: denna.signal }
          );
          const bolag: Traff[] = sida.data.map((b) => ({
            id: `bolag:${b.id}`,
            label: b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" }),
            auxiliaryData: { group: bolagsgrupp, slag: "bolag", mal: b.id, ort: b.address.city }
          }));
          return [...lokala, ...bolag];
        } catch {
          // Avbrutet eller fel: visa kommandona, inte en tom lista.
          return lokala;
        }
      }
    };
  }, [kommandon, text]);

  return (
    <CommandPalette<Traff>
      isOpen={oppen}
      onOpenChange={setOppen}
      searchSource={kalla}
      label={text({ sv: "Kommandopalett", en: "Command palette" })}
      input={
        <CommandPaletteInput
          label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
          placeholder={text({ sv: "Sök bolag eller skriv ett kommando", en: "Search companies or type a command" })}
        />
      }
      emptySearchText={text({ sv: "Inga träffar", en: "No results" })}
      emptyBootstrapText={text({ sv: "Skriv för att söka", en: "Type to search" })}
      renderItem={(item) => {
        const d = item.auxiliaryData;
        return (
          <HStack gap={2} vAlign="center">
            {d?.slag === "bolag" ? (
              <Avatar name={utanBolagsform(item.label)} size="xsm" shape="rounded" tooltip={false} />
            ) : d?.ikon ? (
              <Icon icon={d.ikon} size="sm" color="secondary" />
            ) : null}
            <StackItem size="fill">
              <Text maxLines={1}>{item.label}</Text>
            </StackItem>
            {d?.ort ? <Text type="supporting" color="secondary">{d.ort}</Text> : null}
          </HStack>
        );
      }}
      // Enter och klick landar båda här, och paletten stänger sig själv efteråt.
      onValueChange={(id) => {
        const vald = [...kommandon].find((k) => k.id === id);
        if (id.startsWith("bolag:")) oppnaBolag(id.slice("bolag:".length));
        else if (vald?.auxiliaryData?.slag === "ga") router.push(vald.auxiliaryData.mal);
        else if (vald?.auxiliaryData?.slag === "skapa") skapa(vald.auxiliaryData.mal as "bolag" | "anslutning" | "nyckel");
      }}
    />
  );
}
```

### d. Rutnät med fyra nyckeltal och ett framhävt färgat kort

Fil: `recept-d.tsx`.

Bolag, Kunder, Personer och Att rätta. Etikett överst, talet i Fraunces 2,5 rem med
tabulära siffror, en dämpad rad under. Att rätta är sidans enda framhävda ruta:
`ClickableCard variant="yellow"` (ockratonad i Snajps tema) som länkar till Synk.

Att tänka på:
- `Oversikt.bolag` har databasens svenska nycklar (`kund`, `prospekt`, …) plus `alla`.
- Det nästlade rutnätet ger 4, 2 + 2 eller 1 i bredd; aldrig 3 + 1.
- `Card variant="yellow"` och `ClickableCard variant="yellow"` läser
  `--color-background-yellow`, som `snajpTema.ts` sätter till ockra med 14 % alfa.
- Var talet "Att rätta" kommer ifrån bestämmer vyn (felposterna i senaste körningarna);
  receptet tar det som prop.

```tsx
"use client";

import { Card } from "@astryxdesign/core/Card";
import { ClickableCard } from "@astryxdesign/core/ClickableCard";
import { Grid } from "@astryxdesign/core/Grid";
import { Heading } from "@astryxdesign/core/Heading";
import { VStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import type { Oversikt } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Ett nyckeltal: etikett överst, talet i Fraunces, en dämpad rad under. */
function Tal({ etikett, varde, rad }: Readonly<{ etikett: string; varde: number; rad: string }>) {
  return (
    <VStack gap={2}>
      <Text type="label" color="secondary">
        {etikett}
      </Text>
      {/* font-display = Snajps Fraunces. Inte font-serif (Tailwinds Georgia). */}
      <Text hasTabularNumbers className="font-display" style={{ fontSize: "2.5rem", lineHeight: 1 }}>
        {varde.toLocaleString("sv-SE")}
      </Text>
      <Text type="supporting" color="secondary">
        {rad}
      </Text>
    </VStack>
  );
}

export function Nyckeltal({ oversikt, attRatta, bas = "/crm" }: Readonly<{ oversikt: Oversikt; attRatta: number; bas?: string }>) {
  const { text } = useLocale();
  const alla = oversikt.bolag.alla;
  const kunder = oversikt.bolag.kund ?? 0;

  return (
    <VStack gap={6}>
      <Heading level={1}>{text({ sv: "Översikt", en: "Overview" })}</Heading>
      {/* Två rutnät med två kort i ett yttre: 4 i bredd, 2 + 2 på mellanbredd, 1 på mobil,
          aldrig 3 + 1. Numeriskt columns={4} hade aldrig brutits om. */}
      <Grid columns={{ minWidth: 440, max: 2, repeat: "fit" }} gap={4}>
        <Grid columns={{ minWidth: 200, max: 2, repeat: "fit" }} gap={4}>
          <Card padding={5}>
            <Tal
              etikett={text({ sv: "Bolag", en: "Companies" })}
              varde={alla}
              rad={text({ sv: "i registret", en: "in the register" })}
            />
          </Card>
          <Card padding={5}>
            <Tal
              etikett={text({ sv: "Kunder", en: "Customers" })}
              varde={kunder}
              rad={text({ sv: `${kunder} av ${alla} är kunder`, en: `${kunder} of ${alla} are customers` })}
            />
          </Card>
        </Grid>
        <Grid columns={{ minWidth: 200, max: 2, repeat: "fit" }} gap={4}>
          <Card padding={5}>
            <Tal
              etikett={text({ sv: "Personer", en: "People" })}
              varde={oversikt.personer}
              rad={text({ sv: "kopplade till bolag", en: "linked to companies" })}
            />
          </Card>
          {/* Sidans enda framhävda ruta: ockratonad (variant yellow) och länk till Synk. */}
          <ClickableCard
            label={text({ sv: `Att rätta: ${attRatta}, öppna Synk`, en: `To fix: ${attRatta}, open Sync` })}
            href={`${bas}/synk`}
            variant="yellow"
            padding={5}
          >
            <Tal
              etikett={text({ sv: "Att rätta", en: "To fix" })}
              varde={attRatta}
              rad={text({ sv: "poster som inte kom in", en: "records that did not import" })}
            />
          </ClickableCard>
        </Grid>
      </Grid>
    </VStack>
  );
}
```

### e. Drawer med huvud, flikar och MetadataList i grupper

Fil: `recept-e.tsx`.

Postens panel: `Drawer` från höger, 520 px, byggd med `Layout`. Huvudet är
`DrawerHeader` med avatar, namnet i Fraunces, organisationsnummer och relation, en
Redigera-knapp och stängknappen. Under det runda snabbval (avstängda med förklaring
när uppgiften saknas), flikarna Översikt, Personer (antal) och Källa, och i Översikt
fyra `MetadataList`-grupper där ett tomt värde är en "Lägg till" som öppnar
redigeringen på fältet.

Att tänka på:
- Drawer har ingen egen stängknapp: `onOpenChange` på `DrawerHeader` ger den.
- Avatar 48 (eller 40): kontraktets 44 finns inte.
- `TabList isFullBleed` lägger flikraden kant i kant med panelens innehållsmarginal.
- `IconButton` med `href` blir en länk och tar `target`/`rel` (webbplatsen i ny flik);
  en avstängd `IconButton` förblir en knapp utan mål. `Token` har däremot ingen `target`.
- `MetadataListItem label` måste vara en sträng.

```tsx
"use client";

import { useState } from "react";
import { Building2, CalendarDays, Globe, Hash, Mail, MapPin, Pencil, Phone, UserRound } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent } from "@astryxdesign/core/Layout";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { HStack, VStack } from "@astryxdesign/core/Stack";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Token } from "@astryxdesign/core/Token";
import { RELATIONER, orgnrVisning, type Bolag, type Person } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

type Flik = "oversikt" | "personer" | "kalla";
type Falt = "name" | "org_number" | "relation" | "website" | "email" | "phone" | "owner" | "address" | "customer_since" | "contract_end";

const ETIKETT = { position: "start" as const, width: 148 };

export function BolagPanel({
  bolag,
  personer,
  onOpenChange,
  redigera
}: Readonly<{
  bolag: Bolag | null;
  personer: Person[];
  onOpenChange: (oppen: boolean) => void;
  /** Öppnar redigeringsdialogen, med fokus på ett visst fält om ett ges. */
  redigera: (falt?: Falt) => void;
}>) {
  const { text } = useLocale();
  const [flik, setFlik] = useState<Flik>("oversikt");
  if (!bolag) return null;
  const namn = bolag.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });

  /** Ett tomt värde är en dämpad "Lägg till" som öppnar redigeringen på fältet. */
  const varde = (v: React.ReactNode | null | undefined, falt: Falt) =>
    v == null || v === "" ? (
      <Button label={text({ sv: "Lägg till", en: "Add" })} variant="ghost" size="sm" onClick={() => redigera(falt)} />
    ) : (
      v
    );
  const ikon = (i: typeof Building2) => <Icon icon={i} size="sm" color="secondary" />;

  return (
    <Drawer isOpen onOpenChange={onOpenChange} label={namn} width={520} side="end">
      <Layout
        header={
          <DrawerHeader
            // Avatar 40 eller 48: 44 finns inte bland Avatars storlekar.
            startContent={<Avatar name={namn.replace(/\s+AB$/i, "")} size={48} shape="rounded" tooltip={false} />}
            title={<span className="font-display" style={{ fontSize: "1.375rem" }}>{namn}</span>}
            subtitle={
              <HStack gap={2} vAlign="center">
                <Text color="secondary" hasTabularNumbers>
                  {orgnrVisning(bolag.org_number)}
                </Text>
                {/* Färgen efter relation, som RELATIONSTIL i recept b. */}
                <Badge variant={bolag.relation === "customer" ? "green" : "neutral"} label={text(RELATIONER[bolag.relation])} />
              </HStack>
            }
            endContent={
              <IconButton label={text({ sv: "Redigera", en: "Edit" })} icon={<Icon icon={Pencil} />} variant="ghost" onClick={() => redigera()} />
            }
            // Drawer har ingen egen stängknapp: den här ger den.
            onOpenChange={onOpenChange}
          />
        }
        content={
          <LayoutContent>
            <VStack gap={5}>
              {/* Snabbval: avstängda med förklaring när uppgiften saknas. */}
              <HStack gap={2}>
                <IconButton
                  label={text({ sv: "Mejla", en: "Email" })}
                  icon={<Icon icon={Mail} />}
                  className="rounded-full"
                  href={bolag.email ? `mailto:${bolag.email}` : undefined}
                  isDisabled={!bolag.email}
                  tooltip={bolag.email ? undefined : text({ sv: "E-post saknas", en: "No email" })}
                />
                <IconButton
                  label={text({ sv: "Ring", en: "Call" })}
                  icon={<Icon icon={Phone} />}
                  className="rounded-full"
                  href={bolag.phone ? `tel:${bolag.phone}` : undefined}
                  isDisabled={!bolag.phone}
                  tooltip={bolag.phone ? undefined : text({ sv: "Telefon saknas", en: "No phone" })}
                />
                <IconButton
                  label={text({ sv: "Öppna webbplatsen", en: "Open website" })}
                  icon={<Icon icon={Globe} />}
                  className="rounded-full"
                  href={bolag.website ?? undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  isDisabled={!bolag.website}
                  tooltip={bolag.website ? undefined : text({ sv: "Webbplats saknas", en: "No website" })}
                />
              </HStack>

              <TabList value={flik} onChange={(v) => setFlik(v as Flik)} hasDivider isFullBleed>
                <Tab value="oversikt" label={text({ sv: "Översikt", en: "Overview" })} />
                <Tab value="personer" label={text({ sv: "Personer", en: "People" })} endContent={<Badge label={String(personer.length)} />} />
                <Tab value="kalla" label={text({ sv: "Källa", en: "Source" })} />
              </TabList>

              {/* TabList ritar inga paneler: innehållet för vald flik renderas här. */}
              {flik === "oversikt" ? (
                <VStack gap={5}>
                  <MetadataList title={text({ sv: "Allmänt", en: "General" })} label={ETIKETT}>
                    <MetadataListItem label={text({ sv: "Org.nr", en: "Org. no." })} icon={ikon(Hash)}>
                      {varde(bolag.org_number && orgnrVisning(bolag.org_number), "org_number")}
                    </MetadataListItem>
                    <MetadataListItem label={text({ sv: "Ort", en: "City" })} icon={ikon(MapPin)}>
                      {varde(bolag.address.city, "address")}
                    </MetadataListItem>
                  </MetadataList>
                  <MetadataList title={text({ sv: "Affär", en: "Business" })} label={ETIKETT}>
                    <MetadataListItem label={text({ sv: "Ansvarig", en: "Owner" })} icon={ikon(UserRound)}>
                      {varde(bolag.owner, "owner")}
                    </MetadataListItem>
                    <MetadataListItem label={text({ sv: "Kund sedan", en: "Customer since" })} icon={ikon(CalendarDays)}>
                      {varde(bolag.customer_since && <Timestamp value={bolag.customer_since} format="date" hasTooltip={false} color="primary" />, "customer_since")}
                    </MetadataListItem>
                  </MetadataList>
                  <MetadataList title={text({ sv: "Kontakt", en: "Contact" })} label={ETIKETT}>
                    <MetadataListItem label={text({ sv: "E-post", en: "Email" })} icon={ikon(Mail)}>
                      {varde(bolag.email && <Token label={bolag.email} icon={<Icon icon={Mail} size="sm" />} size="sm" href={`mailto:${bolag.email}`} />, "email")}
                    </MetadataListItem>
                    <MetadataListItem label={text({ sv: "Telefon", en: "Phone" })} icon={ikon(Phone)}>
                      {varde(bolag.phone && <Token label={bolag.phone} icon={<Icon icon={Phone} size="sm" />} size="sm" href={`tel:${bolag.phone}`} />, "phone")}
                    </MetadataListItem>
                  </MetadataList>
                  <MetadataList title={text({ sv: "System", en: "System" })} label={ETIKETT}>
                    <MetadataListItem label={text({ sv: "Ändrad", en: "Updated" })} icon={ikon(CalendarDays)}>
                      {bolag.updated_at ? <Timestamp value={bolag.updated_at} format="relative" /> : null}
                    </MetadataListItem>
                  </MetadataList>
                </VStack>
              ) : null}

              {flik === "personer" ? (
                <VStack gap={3}>
                  {personer.map((p) => {
                    const pn = [p.first_name, p.last_name].filter(Boolean).join(" ");
                    return (
                      <HStack key={p.id} gap={3} vAlign="center">
                        <Avatar name={pn} size="sm" tooltip={false} />
                        <VStack gap={0.5}>
                          <Text weight="semibold">{pn}</Text>
                          {p.title ? <Text type="supporting" color="secondary">{p.title}</Text> : null}
                        </VStack>
                        {p.email ? <Token label={p.email} icon={<Icon icon={Mail} size="sm" />} size="sm" href={`mailto:${p.email}`} /> : null}
                      </HStack>
                    );
                  })}
                </VStack>
              ) : null}

              {flik === "kalla" ? (
                <MetadataList label={ETIKETT}>
                  {bolag.external_ids.map((e) => (
                    <MetadataListItem key={`${e.connection}:${e.id}`} label={e.connection}>
                      <HStack gap={2} vAlign="center">
                        <Text type="code">{e.id}</Text>
                        {e.last_seen_at ? <Timestamp value={e.last_seen_at} format="relative" /> : null}
                      </HStack>
                    </MetadataListItem>
                  ))}
                </MetadataList>
              ) : null}
            </VStack>
          </LayoutContent>
        }
      />
    </Drawer>
  );
}
```


---

## Hur exemplen kontrollerades

Varje `tsx`-block i den här filen (54 exempel) och de fem recepten lades i egna filer och
typkontrollerades med `tsc` mot `node_modules` i det här repot (strict, `moduleResolution:
bundler`, `jsx: react-jsx`, `@/*` mot repots rot) den 2026-11-26: inga fel. Kontrollen
fällde fem saker som står som fällor ovan: lucide-komponent i en `icon`-prop av typen
`ReactNode` (Button, IconButton, Token), `string` till `DateInput.value` och `"gray"`
till `Badge`. Utseendet är beskrivet från Astryx referensbilder, inte renderat i Snajps
tema: allt som syns ska fortfarande ses i bild enligt projektets regel.

Källor: `npx astryx --dense component <Namn>` och `hook <namn>` (CLI 0.7.17),
typerna i `node_modules/@astryxdesign/core/dist`, mallarna `shell-side-nav`,
`dashboard`, `detail-page` och blocken `CommandPalette*`, `SideNavWithHeaderMenu`,
`TableBulkActionsTable` i klonen, och referensbilderna i
`.github/visual-baseline/shots`.

