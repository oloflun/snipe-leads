# Photography credits

The four photographs on the Snajp landing page come from Unsplash. They are used
under the [Unsplash License](https://unsplash.com/license), which permits
commercial use without attribution. Credit is given anyway: these are someone's
photographs, and vendoring a copy into this repository without naming the
photographer would not be right.

| File | Photographer | Source |
|---|---|---|
| `stockholm-golden.webp` | [@trapnation](https://unsplash.com/@trapnation) | [unsplash.com/photos/1730653784025-2266f3baa0f8](https://unsplash.com/photos/1730653784025-2266f3baa0f8) |
| `gamla-stan.webp` | [@gwendal](https://unsplash.com/@gwendal) | [unsplash.com/photos/1714930723042-8a4b7bca8a14](https://unsplash.com/photos/1714930723042-8a4b7bca8a14) |
| `desk.webp` | [@photo_sergiub](https://unsplash.com/@photo_sergiub) | [unsplash.com/photos/1611269154421-4e27233ac5c7](https://unsplash.com/photos/1611269154421-4e27233ac5c7) |
| `facade.webp` | [@nasa](https://unsplash.com/@nasa) | [unsplash.com/photos/1564515836665-083f987752a8](https://unsplash.com/photos/1564515836665-083f987752a8) |

Usernames were read from each photo's Unsplash page. If a display name is wanted
instead of the handle, open the source link.

## Processing

Downloaded at their display width, longest edge capped at 2200px, re-encoded to
WebP at quality 78. Total went from 2996 KB to 1147 KB, a 62% reduction, with no
visible loss at the sizes the page renders them.

They were hotlinked from `images.unsplash.com` during development. Serving them
from `public/` removes a third-party dependency from the critical render path:
the hero photograph is the page's largest contentful paint, and it should not
depend on another company's CDN being reachable.
