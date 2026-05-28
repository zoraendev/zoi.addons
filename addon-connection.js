const BASE_URL = "https://api.zoraen.com";
const API_PREFIX = "/api/production";
const API_KEY = "9we92sds";
const ADDON_API_KEY =
  process.env.ADDON_API_KEY ??
  "hhVjv5JzUE4Gq8Td:YCj7HQbvWbKoAUwFXaOAx8QDruGqYGnNHn424io9JuxaScU/vh+/M3uh/Q==:L56EkacmQKjLmDAp9X1CyQ==";

async function readResponse(response) {
  const contentType = response.headers.get("content-type") ?? "";
  const rawText = await response.text();

  if (!rawText) {
    return {
      contentType,
      rawText: "",
      json: null,
    };
  }

  if (contentType.includes("application/json")) {
    try {
      return {
        contentType,
        rawText,
        json: JSON.parse(rawText),
      };
    } catch {
      return {
        contentType,
        rawText,
        json: null,
      };
    }
  }

  return {
    contentType,
    rawText,
    json: null,
  };
}

async function validateAddonConnection() {
  const url = `${BASE_URL}${API_PREFIX}/addons/vladdonconnection`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "x-api-key": API_KEY,
        "x-addonapi-key": ADDON_API_KEY,
      },
    });

    const payload = await readResponse(response);

    console.log("URL:", url);
    console.log("Status:", response.status);
    console.log("Content-Type:", payload.contentType || "unknown");
    console.log("Response:", payload.json);

    if (!payload.json) {
      console.log("Raw Response:", payload.rawText);
    }
  } catch (error) {
    console.error("Request failed:", error);
  }
}

validateAddonConnection();
