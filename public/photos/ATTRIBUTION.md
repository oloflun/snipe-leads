# Photography credits

The four photographs on the Snajp landing page come from Unsplash. They are used
under the [Unsplash License](https://unsplash.com/license), which permits
commercial use without attribution. Credit is given anyway: these are someone's
photographs, and vendoring a copy into this repository without naming the
photographer would not be right.

| File | Photographer | Source |
|---|---|---|
| `goteborg-golden.webp` | Aron Fjell, [@addekalk](https://unsplash.com/@addekalk) | [unsplash.com/photos/wmrYHqSHoek](https://unsplash.com/photos/wmrYHqSHoek) |
| `haga.webp` | Patrick Federi, [@federi](https://unsplash.com/@federi) | [unsplash.com/photos/U5PrXTqxF2A](https://unsplash.com/photos/U5PrXTqxF2A) |
| `desk.webp` | [@photo_sergiub](https://unsplash.com/@photo_sergiub) | [unsplash.com/photos/1611269154421-4e27233ac5c7](https://unsplash.com/photos/1611269154421-4e27233ac5c7) |
| `facade.webp` | [@nasa](https://unsplash.com/@nasa) | [unsplash.com/photos/1564515836665-083f987752a8](https://unsplash.com/photos/1564515836665-083f987752a8) |

Usernames were read from each photo's Unsplash page. If a display name is wanted
instead of the handle, open the source link.

## Processing

Downloaded at their display width, longest edge capped at 2200px, re-encoded to
WebP at quality 78, with no visible loss at the sizes the page renders them.

`haga.webp` is the exception on both counts. The original is portrait, so it was
cropped to the upper band that holds the facade, the walker and the perspective;
the lower 40% was empty paving. Cobblestone texture is expensive to encode, so it
sits at 2000px and quality 74 (524 KB against 666 KB at the standard settings).
A 1:1 comparison against the uncompressed crop showed no visible difference.

The two Stockholm photographs this pair replaced were removed when the place copy
moved to Gothenburg.

They were hotlinked from `images.unsplash.com` during development. Serving them
from `public/` removes a third-party dependency from the critical render path:
the hero photograph is the page's largest contentful paint, and it should not
depend on another company's CDN being reachable.
