# Official artwork and attribution

The wordmark and square monogram come from the manufacturer's public website
to identify the compatible product. This unofficial personal integration is
not an Evonic or Home Assistant product or endorsement. Artwork remains its
owner's property and is excluded from this project's MIT source-code licence.
No ownership of the marks or manufacturer endorsement is claimed; see NOTICE.

Sources retrieved 8 November 2026 from the [official contact page](https://evonicfires.co.uk/contact-us/):

| Asset | Official source | Original dimensions |
| --- | --- | --- |
| Wordmark | [Evonic Flat Logo 2026](https://evonicfires.co.uk/wp-content/uploads/2026/03/Evonic-Flat-Logo-2026.png) | 1997 × 482 |
| Monogram | [Evonic site icon](https://evonicfires.co.uk/wp-content/uploads/2025/04/cropped-favicon.png) | 512 × 512 |

Original SHA-256:

```text
wordmark d35818b1902d61a2bf9bf21c9059c71304f1f5ec9d8ba44c529a269d3971714b
monogram 2b51b920a541027d774891a5975429eca420c605a8078ec5a43a5cab1cf222d7
```

`tools/build_brand.ps1` trims transparent margins and resizes proportionally,
preserving artwork, colour and transparency. It creates 256/512-square
`icon.png` / `icon@2x.png`, plus landscape `logo.png` / `logo@2x.png` inside
`custom_components/evonic_ble/brand`. Square padding only preserves proportions.
No generated mark, recolouring or Home Assistant badge is used.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_brand.ps1 `
  -LogoSource <downloaded-wordmark.png> -IconSource <downloaded-site-icon.png> `
  -OutputDirectory custom_components/evonic_ble/brand
```

Packaging follows [HA branding guidance](https://contributors.home-assistant.io/core/integrations/brands/).
Current HA supports this local folder without a shared brands-repository
submission. Optional dark-specific images are not supplied. Integration
branding does not replace entity icons or dashboard climate colouring.
