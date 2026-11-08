# Deterministic packaging of official manufacturer PNG artwork; no redrawing.
param(
  [Parameter(Mandatory=$true)][string]$LogoSource,
  [Parameter(Mandatory=$true)][string]$IconSource,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
public static class EvonicBrandPack {
  public static Rectangle Bounds(Bitmap image) {
    int left=image.Width, top=image.Height, right=-1, bottom=-1;
    for(int y=0;y<image.Height;y++) for(int x=0;x<image.Width;x++)
      if(image.GetPixel(x,y).A>0) {
        left=Math.Min(left,x);top=Math.Min(top,y);
        right=Math.Max(right,x);bottom=Math.Max(bottom,y);
      }
    if(right<0) throw new ArgumentException("Empty artwork");
    return Rectangle.FromLTRB(left,top,right+1,bottom+1);
  }
  public static void Save(Bitmap source, Rectangle crop, int width, int height, string path, bool square) {
    using(var output=new Bitmap(width,height,PixelFormat.Format32bppArgb))
    using(var draw=Graphics.FromImage(output)) {
      draw.Clear(Color.Transparent);
      draw.CompositingMode=CompositingMode.SourceCopy;
      draw.CompositingQuality=CompositingQuality.HighQuality;
      draw.InterpolationMode=InterpolationMode.HighQualityBicubic;
      draw.PixelOffsetMode=PixelOffsetMode.HighQuality;
      float scale=square?Math.Min((float)width/crop.Width,(float)height/crop.Height):(float)height/crop.Height;
      float w=crop.Width*scale,h=crop.Height*scale;
      draw.DrawImage(source,new RectangleF((width-w)/2,(height-h)/2,w,h),crop,GraphicsUnit.Pixel);
      output.Save(path,ImageFormat.Png);
    }
  }
}
'@
$brandOut=[System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($brandOut) | Out-Null
$brandLogo=[System.Drawing.Bitmap]::new([System.IO.Path]::GetFullPath($LogoSource))
$brandIcon=[System.Drawing.Bitmap]::new([System.IO.Path]::GetFullPath($IconSource))
try {
  $logoCrop=[EvonicBrandPack]::Bounds($brandLogo)
  $iconCrop=[EvonicBrandPack]::Bounds($brandIcon)
  $logoHighHeight=[Math]::Min(512,$logoCrop.Height)
  if($logoHighHeight -lt 256) { throw 'Official logo is too small for an HD asset' }
  $logoHeight=[int][Math]::Round($logoHighHeight/2.0)
  $logoWidth=[int][Math]::Round($logoHeight*$logoCrop.Width/$logoCrop.Height)
  $logoHighWidth=[int][Math]::Round($logoHighHeight*$logoCrop.Width/$logoCrop.Height)
  [EvonicBrandPack]::Save($brandLogo,$logoCrop,$logoWidth,$logoHeight,(Join-Path $brandOut 'logo.png'),$false)
  [EvonicBrandPack]::Save($brandLogo,$logoCrop,$logoHighWidth,$logoHighHeight,(Join-Path $brandOut 'logo@2x.png'),$false)
  [EvonicBrandPack]::Save($brandIcon,$iconCrop,256,256,(Join-Path $brandOut 'icon.png'),$true)
  [EvonicBrandPack]::Save($brandIcon,$iconCrop,512,512,(Join-Path $brandOut 'icon@2x.png'),$true)
} finally {
  $brandLogo.Dispose();$brandIcon.Dispose()
}
Get-ChildItem -LiteralPath $brandOut -Filter '*.png' | Select-Object Name,Length
