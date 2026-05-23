declare const Deno: {
  serve: (handler: (request: Request) => Response | Promise<Response>) => void;
};
