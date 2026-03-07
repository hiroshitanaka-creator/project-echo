const http = require('http');

const server = http.createServer((req, res) => {
// ブラウザに正常終了（200 OK）を返し、日本語が化けないように設定します
res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });

// 画面に表示するメッセージです
res.end('<h1>Project Echo: 拠点構築完了</h1><p>Cloud Runへのデプロイに成功しました。ここから透明性防衛のロジックを組み込みます。</p>');
});

// Cloud Runの環境に合わせてポート番号を取得します
const port = process.env.PORT || 8080;

// '0.0.0.0' を指定することで、外部からのアクセスをすべて許可します
server.listen(port, '0.0.0.0', () => {
console.log('Server is running on port ' + port);
});
