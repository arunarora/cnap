local http = require("resty.http")
local cjson = require("cjson")

local oidcHandler = {
    PRIORITY = 1000,
    VERSION = "0.0.1",
}

function oidcHandler:access(conf)
    kong.log.debug("oidc access handler called")


    -- Exit with error if no Authorization header is present in the request
    if not ngx.var.http_authorization then
        ngx.log(ngx.ERR, "Authorization Header missing in request")
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end

    -- Validate the access token with the identity provider
    local httpc = http.new()
    local res, err = httpc:request_uri(conf.token_validation_url, {
        method = "POST",
        body = "client_id=" .. conf.client_id .. "&client_secret=" .. conf.client_secret .. "&token=" .. ngx.var.http_authorization,
        headers = {
            ["Content-Type"] = "application/x-www-form-urlencoded",
        },
    })

    ngx.log(ngx.NOTICE, "Entering access function")
    -- ngx.log(ngx.NOTICE, "body ", cjson.encode(request_options))
    ngx.log(ngx.NOTICE, "Plugin Configuration :", cjson.encode(conf))

    if not res then
        ngx.log(ngx.ERR, "Failed to introspect token: ", err)
        return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end

    if res.status ~= 200 then
        ngx.log(ngx.ERR, "Token introspection failed with status: ", res.status)
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end

    -- Parse the introspection response
    local introspection_result = cjson.decode(res.body)
    ngx.log(ngx.NOTICE, "Introspection result: ", res.body)

    -- Check if the token is active
    if not introspection_result.active then
        ngx.log(ngx.ERR, "Access token is not active")
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end

    -- Add introspection result to request headers
    ngx.req.set_header("X-User-Id", introspection_result.sub)
    ngx.req.set_header("X-Username", introspection_result.username)

    ngx.log(ngx.INFO, "Token introspection successful")

    -- Close the HTTP connection
    httpc:close()
end

return oidcHandler