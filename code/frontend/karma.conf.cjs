module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma'),
    ],
    client: {
      jasmine: {},
      clearContext: false,
    },
    reporters: ['progress', 'kjhtml'],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    customLaunchers: {
      ChromeHeadlessNoSandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox', '--disable-dev-shm-usage'],
      },
    },
    browsers: ['ChromeHeadlessNoSandbox'],
    singleRun: false,
    restartOnFileChange: true,
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/elvir-frontend'),
      subdir: '.',
      reporters: [{ type: 'html' }, { type: 'text-summary' }, { type: 'json-summary' }],
      // Colores del informe HTML: Istanbul marca verde si la métrica ≥ watermarks[X][1] (por defecto 80%).
      // Las ramas suelen quedar amarillas ~50% aunque `check.global.branches` (45) pase; [45,50] alinea verde con ≥50%.
      watermarks: {
        statements: [50, 80],
        branches: [45, 50],
        functions: [50, 80],
        lines: [50, 80],
      },
      check: {
        global: {
          // Umbrales alineados con la suite actual (CI); subir con nuevos tests.
          statements: 75,
          branches: 45,
          functions: 85,
          lines: 75,
        },
      },
    },
  });
};
