# 画像生成AI用プロンプト

## 用途
テキストから画像を生成するAI向け（Stable Diffusion, DALL-E, Midjourney等）

## プロンプト構造

```
[被写体/主題], [スタイル/画風], [構図/アングル], [照明/雰囲気], [品質修飾子]
```

## テンプレート

### ポートレート写真風
```
portrait of [人物の特徴], [表情], [服装],
shot on Canon EOS R5, 85mm lens, f/1.8,
soft natural lighting, bokeh background,
professional photography, high resolution, 8k
```

### イラスト・アニメ風
```
[キャラクターの説明], [ポーズ/動作],
[背景の説明],
anime style, vibrant colors, detailed illustration,
by [アーティスト名風], trending on artstation
```

### 風景画風
```
[場所/シーン], [時間帯], [天候],
cinematic composition, dramatic lighting,
landscape photography, wide angle,
golden hour, atmospheric perspective, 4k wallpaper
```

### プロダクトデザイン
```
[製品の説明], minimalist design,
studio lighting, white background,
product photography, commercial shot,
clean aesthetic, high detail, professional
```

## ネガティブプロンプト例

```
ugly, deformed, noisy, blurry, low quality,
bad anatomy, bad proportions, extra limbs,
text, watermark, signature, out of frame
```

## 対応AI
- Midjourney
- DALL-E 3
- Stable Diffusion
- Adobe Firefly
- Leonardo.ai
