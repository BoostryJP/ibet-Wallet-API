from web3.middleware.formatting import FormattingMiddlewareBuilder

# NOTE: The correct type is likely FormattingMiddlewareBuilder,
# but `type` is used here to avoid a type error when passing it to `web3.middleware_onion.inject`.
ExtraDataToPOAMiddleware: type[FormattingMiddlewareBuilder]
