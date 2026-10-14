# Tiny local web server for PixBrik. Uses only what ships with Windows.
# Started by "Start PixBrik (Windows).bat". Close the window to stop it.

$root = $PSScriptRoot
$types = @{
  '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'; '.css' = 'text/css; charset=utf-8'
  '.json' = 'application/json'; '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.jpeg' = 'image/jpeg'
  '.svg' = 'image/svg+xml'; '.ico' = 'image/x-icon'; '.glb' = 'model/gltf-binary'; '.gltf' = 'model/gltf+json'
  '.md' = 'text/plain; charset=utf-8'; '.txt' = 'text/plain; charset=utf-8'
}

$listener = $null
foreach ($port in 8080..8099) {
  $try = New-Object System.Net.HttpListener
  $try.Prefixes.Add("http://localhost:$port/")
  try { $try.Start(); $listener = $try; break } catch { $try.Close() }
}
if (-not $listener) {
  Write-Host 'Could not find a free port between 8080 and 8099.' -ForegroundColor Red
  Read-Host 'Press Enter to close'
  exit 1
}

$url = "http://localhost:$port/"
Write-Host ''
Write-Host '  PixBrik is running at ' -NoNewline
Write-Host $url -ForegroundColor Yellow
Write-Host '  Keep this window open while you use it. Close it to stop PixBrik.'
Write-Host ''
Start-Process $url

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $res = $ctx.Response
    try {
      $path = [System.Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath).TrimStart('/')
      if ($path -eq '') { $path = 'index.html' }
      $file = [System.IO.Path]::GetFullPath((Join-Path $root $path))
      if ($file.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path $file -PathType Leaf)) {
        $bytes = [System.IO.File]::ReadAllBytes($file)
        $ext = [System.IO.Path]::GetExtension($file).ToLower()
        if ($types.ContainsKey($ext)) { $res.ContentType = $types[$ext] } else { $res.ContentType = 'application/octet-stream' }
        $res.Headers.Add('Cache-Control', 'no-cache')
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
      } else {
        $res.StatusCode = 404
        $msg = [System.Text.Encoding]::UTF8.GetBytes('Not found')
        $res.OutputStream.Write($msg, 0, $msg.Length)
      }
    } catch {
      $res.StatusCode = 500
    } finally {
      $res.OutputStream.Close()
    }
  }
} finally {
  $listener.Stop()
}
