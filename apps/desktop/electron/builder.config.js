module.exports = {
  appId: "com.sessionscribe.desktop",
  productName: "SessionScribe",
  directories: { output: "dist" },
  files: ["**/*"],
  nsis: { oneClick: true, perMachine: false, allowToChangeInstallationDirectory: false }
};