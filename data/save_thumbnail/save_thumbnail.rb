f=UI.select_directory
if f
  pngs=File.join(f, 'PNGS')
  dir=Dir.mkdir(pngs) unless File.exist?(pngs)
  Dir.glob("#{f}/*.skp").each{|skp|
    s=Sketchup.open_file(skp)
    if s
      p skp
      p png=File.join(pngs, File.basename(skp, ".*")+".png")
      Sketchup.active_model.save_thumbnail(png)
    end
  }
  UI.openURL("file::///#{dir}")
  Sketchup.active_model.close
end