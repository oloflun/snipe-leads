import { readJsonBody } from "@/lib/http/json";

type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type ChatCompletionOptions = {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  responseFormat?: "json_object" | "text";
};

type ChatCompletionResult = {
  content: string;
  model: string;
  provider: "deepseek" | "openai";
};

function getProvider(): "deepseek" | "openai" {
  const provider = (process.env.LLM_PROVIDER ?? "deepseek").toLowerCase();
  return provider === "openai" ? "openai" : "deepseek";
}

function getApiConfig(provider: "deepseek" | "openai") {
  if (provider === "openai") {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error("Missing OPENAI_API_KEY");
    }

    return {
      apiKey,
      baseUrl: process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1",
      defaultModel: process.env.LLM_REFINE_MODEL ?? "gpt-4o-mini"
    };
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error("Missing DEEPSEEK_API_KEY");
  }

  return {
    apiKey,
    baseUrl: process.env.DEEPSEEK_BASE_URL ?? "https://api.deepseek.com/v1",
    defaultModel: process.env.LLM_REFINE_MODEL ?? "deepseek-chat"
  };
}

export async function createChatCompletion(options: ChatCompletionOptions): Promise<ChatCompletionResult> {
  const provider = getProvider();
  const config = getApiConfig(provider);
  const model = options.model ?? config.defaultModel;

  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${config.apiKey}`
    },
    body: JSON.stringify({
      model,
      messages: options.messages,
      temperature: options.temperature ?? 0.4,
      max_tokens: options.maxTokens ?? 1200,
      response_format: options.responseFormat === "json_object" ? { type: "json_object" } : undefined
    })
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`LLM request failed (${response.status}): ${errorBody}`);
  }

  // Statuskoden är redan kontrollerad ovan, men 200 garanterar ingen kropp:
  // en avhuggen strömning eller en proxy-sida ger tomt/HTML här också.
  const payload = await readJsonBody<{
    choices?: Array<{ message?: { content?: string } }>;
    model?: string;
  }>(response);

  const content = payload?.choices?.[0]?.message?.content?.trim();
  if (!content) {
    throw new Error("LLM returned an empty response");
  }

  return {
    content,
    model: payload?.model ?? model,
    provider
  };
}