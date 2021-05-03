import connexion


def create_app(host, port):

    app = connexion.FlaskApp(
        __name__,
        specification_dir='openapi/',
        debug=True,
        options={"swagger_url": ""}
    )

    options = {"swagger_ui": True}
    app.add_api('openapi.yaml',
                options=options,
                arguments={'title': 'PerfectFit server'},
                strict_validation=True,
                validate_responses=True
                )

    return app.app


if __name__ == "__main__":
    host = '0.0.0.0'
    port = 8080
    app = create_app(host, port)
    app.run(host=host, port=port, debug=True)
