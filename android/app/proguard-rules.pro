# Retrofit reads method annotations and generic return types at runtime. Keeping the API
# interface prevents R8 full mode from replacing an otherwise-unused response DTO with
# Object, which would make kotlinx.serialization look for an unsafe `Any` serializer.
-keepattributes Signature,RuntimeVisibleAnnotations,RuntimeVisibleParameterAnnotations,AnnotationDefault
-keep interface com.incaof.app.core.network.IcoApi { *; }
