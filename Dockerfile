# The test shop in a locked container. See "Hosting" in docs/test_page.md.

# The debug image has a shell. It only makes the empty log folder.
FROM gcr.io/distroless/python3-debian13:debug AS build
RUN ["/busybox/mkdir", "-p", "/out/shop"]

# The final image has only Python: no shell, no package manager and no other tools.
FROM gcr.io/distroless/python3-debian13:nonroot
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Root owns the code, so the server user cannot change it.
COPY src/shop src/shop
# The log folder is the only folder that the server user owns.
COPY --from=build --chown=65534:65534 /out /app/data

# The user "nobody" has no home, no shell and no files, except the log folder.
USER 65534:65534
EXPOSE 8000
ENTRYPOINT ["/usr/bin/python3", "-m", "src.shop"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
