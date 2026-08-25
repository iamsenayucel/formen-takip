import { runtimeConfig } from "../config/runtimeConfig";

// Yalnızca geliştirme/demo içindir ve backend AUTH_BYPASS seçeneğini yansıtır.
// Backend, ENVIRONMENT=development dışında bağımsız olarak reddettiğinden bu sabit
// yalnızca local build'leri etkiler; gerçek deployment'ı etkilemez.
export const AUTH_BYPASS_ENABLED = runtimeConfig.authBypassEnabled();
