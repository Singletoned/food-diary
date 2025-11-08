# App Icons for Chompix PWA

This directory should contain app icons in various sizes for iOS and Android devices.

## Required Icon Sizes

Create PNG icons in the following sizes:
- **72x72** - icon-72x72.png
- **96x96** - icon-96x96.png
- **128x128** - icon-128x128.png
- **144x144** - icon-144x144.png
- **152x152** - icon-152x152.png (iOS)
- **180x180** - icon-180x180.png (iOS)
- **192x192** - icon-192x192.png (Android)
- **384x384** - icon-384x384.png
- **512x512** - icon-512x512.png (Android)

## Design Guidelines

### iOS
- Use a **square** image (no transparency)
- iOS will automatically round the corners
- Keep important content **centered** and away from edges
- Use the theme color: `#00d1b2` (Bulma's turquoise/teal)

### Android
- Square images work for all versions
- Maskable icons should have important content in the **safe zone** (80% of the icon)
- Android may clip icons into different shapes

## Quick Icon Generation

You can use online tools to generate all sizes from a single high-resolution image:

1. **PWA Asset Generator**: https://www.pwabuilder.com/imageGenerator
2. **RealFaviconGenerator**: https://realfavicongenerator.net/
3. **App Icon Generator**: https://www.appicon.co/

### Using a Simple Design

For now, you can create a simple icon with:
- **Background**: `#00d1b2` (Chompix theme color)
- **Symbol**: A food emoji like 🍽️ or text "Chompix"
- **Style**: Clean and minimal

## Temporary Solution

Until you create proper icons, you can use a solid color placeholder:

```bash
# Install ImageMagick if not available
# Create placeholder icons
convert -size 512x512 xc:'#00d1b2' -gravity center -pointsize 200 -fill white -annotate +0+0 '🍽️' icon-512x512.png
convert icon-512x512.png -resize 384x384 icon-384x384.png
convert icon-512x512.png -resize 192x192 icon-192x192.png
convert icon-512x512.png -resize 180x180 icon-180x180.png
convert icon-512x512.png -resize 152x152 icon-152x152.png
convert icon-512x512.png -resize 144x144 icon-144x144.png
convert icon-512x512.png -resize 128x128 icon-128x128.png
convert icon-512x512.png -resize 96x96 icon-96x96.png
convert icon-512x512.png -resize 72x72 icon-72x72.png
```

## Testing Your Icons

1. Open your PWA on your device
2. Add to home screen (iOS: Share → Add to Home Screen)
3. Check that the icon appears correctly on your home screen
4. Launch the app and verify the splash screen uses the correct icon
