import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";
import { createApp } from "vue";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import App from "./App.vue";

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "light",
    themes: {
      light: {
        dark: false,
        colors: {
          primary: "#0B6E4F",
          secondary: "#2860C4",
          accent: "#2860C4",
          error: "#B83B34",
          warning: "#A36A00",
          info: "#2860C4",
          success: "#0B6E4F",
          background: "#F4F7F6",
          surface: "#FFFFFF",
        },
      },
    },
  },
  defaults: {
    VBtn: {
      variant: "flat",
    },
    VCard: {
      elevation: 0,
      flat: true,
      border: true,
      rounded: "lg",
    },
    VTextField: {
      variant: "outlined",
      density: "comfortable",
    },
    VSelect: {
      variant: "outlined",
      density: "comfortable",
    },
    VDialog: {
      maxWidth: 720,
    },
  },
});

createApp(App).use(vuetify).mount("#app");
