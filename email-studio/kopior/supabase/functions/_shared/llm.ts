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
  const provider = (Deno.env.get("LLM_PROVIDER") ?? "deepseek").toLowerCase();
  return provider === "openai" ? "openai" : "deepseek";
}

function getApiConfig(provider: "deepseek" | "openai") {
  if (provider === "openai") {
    const apiKey = Deno.env.get("OPENAI_API_KEY");
    if (!apiKey) {
      throw new Error("Missing OPENAI_API_KEY");
    }

    return {
      apiKey,
      baseUrl: Deno.env.get("OPENAI_BASE_URL") ?? "https://api.openai.com/v1",
      defaultModel: Deno.env.get("LLM_REFINE_MODEL") ?? "gpt-4o-mini"
    };
  }

  const apiKey = Deno.env.get("DEEPSEEK_API_KEY");
  if (!apiKey) {
    throw new Error("Missing DEEPSEEK_API_KEY");
  }

  return {
    apiKey,
    baseUrl: Deno.env.get("DEEPSEEK_BASE_URL") ?? "https://api.deepseek.com/v1",
    defaultModel: Deno.env.get("LLM_REFINE_MODEL") ?? "deepseek-chat"
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

  const payload = await response.json();
  const content = payload.choices?.[0]?.message?.content?.trim();

  if (!content) {
    throw new Error("LLM returned an empty response");
  }

  return {
    content,
    model: payload.model ?? model,
    provider
  };
}