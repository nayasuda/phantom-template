# Draw.io Swimlane Generator Skill

## Description
テキストの手順書から、配色とレイアウトが整ったDraw.io形式のスイムレーン図(XML)を生成し、Google Driveへ保存するスキル。
{{COMPANY_NAME}}のブランドカラー（#00abdc）を基調とした、プロフェッショナルで読みやすいフローチャートを作成する。

## Color Palette (MerryBiz Style)
- **Primary**: `#00abdc` (ヘッダー、主要なステップ)
- **Secondary**: `#f2f2f2` (背景、スイムレーン本体)
- **Text**: `#333333` (読みやすさ重視)
- **Stroke**: `#cccccc` (境界線)

## XML Structure Best Practices
`stackLayout` を使用して、要素の追加や削除時に自動的にレイアウトが調整される構造を採用する。

### スイムレーンの基本構造
```xml
<mxGraphModel>
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <!-- プール (全体の枠) -->
    <mxCell id="pool" value="プロセス名" style="swimlane;html=1;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;fontColor=#ffffff;fillColor=#00abdc;strokeColor=#00abdc;" vertex="1" parent="1">
      <mxGeometry x="40" y="40" width="600" height="400" as="geometry" />
    </mxCell>
    <!-- レーン (担当者ごとの区切り) -->
    <mxCell id="lane1" value="担当者A" style="swimlane;html=1;childLayout=stackLayout;horizontal=0;startSize=30;horizontalStack=1;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;fillColor=#ffffff;strokeColor=#cccccc;" vertex="1" parent="pool">
      <mxGeometry x="0" y="30" width="600" height="120" as="geometry" />
    </mxCell>
  </root>
</mxGraphModel>
```

### XML生成の注意点
- **Edge Routing**: エッジ（矢印）を定義する際、`<Array points="...">` タグは使用しないこと。Draw.ioで読み込みエラー（Could not add object Array）の原因になる。経路は自動レイアウトに任せるか、`exitX/entryX` 属性のみで制御すること。

## Usage Flow
1. **XML生成**: 手順書の内容に基づき、上記の構造でXMLを生成する。
2. **一時保存**: `write_file` を使用して、`tmp/process_flow.drawio` として保存する。
3. **Drive転送**: `scripts/save_to_drive.py` を実行して、Google Driveの指定フォルダ（またはルート）へアップロードする。
   ```bash
   python3 scripts/save_to_drive.py tmp/process_flow.drawio --folder "Phantom Uploads"
   ```
4. **後片付け**: アップロード完了後、`rm tmp/process_flow.drawio` で一時ファイルを削除する。

## Example Usage: Webサーバー死活監視手順
成功事例として、以下の構成で依頼すると、整理されたスイムレーン図が生成される。

### 入力プロンプトの例
```text
以下の手順をDraw.ioのスイムレーン図（XML）にして。
担当者は「監視システム」「運用担当者」「インフラエンジニア」の3名。

1. [監視システム] 5分おきにWebサーバーのステータスを確認
2. [監視システム] 異常を検知したらSlackで通知
3. [運用担当者] 通知を確認し、一次切り分けを実施
4. [運用担当者] 再起動で直らなければインフラエンジニアへエスカレーション
5. [インフラエンジニア] ログ調査と根本原因の特定・修正
6. [インフラエンジニア] 復旧完了をSlackで報告
```

### 出力のポイント
- **MerryBizカラーの適用**: プールのヘッダーに `#00abdc` を使用し、フォントカラーを白に設定。
- **stackLayoutの活用**: `childLayout=stackLayout` を設定することで、各レーン内の要素が重ならず、自動的に整列される。
- **3レーン構成**: `pool` の子要素として、3つの `swimlane`（レーン）を定義し、それぞれにステップを配置。

## Tips
- ステップが多い場合は、`pool` と `lane` の `height` を動的に調整すること。
- 各ステップの `mxCell` は、対応する `lane` の `id` を `parent` に指定すること。
- `style` に `rounded=1` を加えると、よりモダンな印象になる。
