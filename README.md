# volapuktranslate

ヴォラピュク語向けの、精度優先の翻訳ツールです。曖昧な箇所を流暢さでごまかさず、検査結果とあわせて提示する方針で作りました。現代中国語への翻訳ワークベンチ [zhtranslate](https://github.com/Arbeit2025/zhtranslate) の前作にあたります。

## 構成

- Flask アプリ本体（`app.py` ほか）。形態素解析や辞書まわりのモジュールを分割しています
- Render へのデプロイ用に `render.yaml` を同梱。手順は [DEPLOY.md](DEPLOY.md) を参照

## 起動方法

```bash
pip install -r requirements.txt
python app.py
```

## ライセンス

MIT License（[LICENSE](LICENSE) を参照）
