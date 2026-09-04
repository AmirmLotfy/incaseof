import { CfnOutput, Duration, RemovalPolicy, Stack } from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface HostingProps {
  readonly environment: IcoEnvironment;
  readonly httpApi: apigw.IHttpApi;
  readonly hostedZoneId?: string;
  readonly hostedZoneName?: string;
  readonly existingApiDomainRegionalName?: string;
  readonly existingApiDomainHostedZoneId?: string;
}

/** Private static origins and the canonical public edge for the hackathon demo. */
export class Hosting extends Construct {
  readonly marketingBucket: s3.Bucket;
  readonly responderBucket: s3.Bucket;
  readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: HostingProps) {
    super(scope, id);

    const production = props.environment.name === "prod";
    const removalPolicy = production ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;
    const bucket = (name: string) => new s3.Bucket(this, name, {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy,
      autoDeleteObjects: false,
    });
    this.marketingBucket = bucket("MarketingOrigin");
    this.responderBucket = bucket("ResponderOrigin");

    const zone = props.hostedZoneId && props.hostedZoneName
      ? route53.HostedZone.fromHostedZoneAttributes(this, "Zone", {
          hostedZoneId: props.hostedZoneId,
          zoneName: props.hostedZoneName,
        })
      : undefined;
    const certificate = zone
      ? new acm.Certificate(this, "EdgeCertificate", {
          domainName: "incaof.com",
          subjectAlternativeNames: ["www.incaof.com", "api.incaof.com"],
          validation: acm.CertificateValidation.fromDns(zone),
        })
      : undefined;

    const rewrite = new cloudfront.Function(this, "RequestRewrite", {
      runtime: cloudfront.FunctionRuntime.JS_2_0,
      code: cloudfront.FunctionCode.fromInline(`
function handler(event) {
  var request = event.request;
  var host = request.headers.host && request.headers.host.value;
  if (host === "www.incaof.com") {
    return { statusCode: 301, statusDescription: "Moved Permanently", headers: { location: { value: "https://incaof.com" + request.uri } } };
  }
  if (request.uri.indexOf("/r/") === 0) request.uri = "/r/__token/index.html";
  else if (request.uri.indexOf("/i/") === 0) request.uri = "/i/__token/index.html";
  else if (request.uri.slice(-1) === "/") request.uri += "index.html";
  else if (request.uri.split("/").pop().indexOf(".") === -1) request.uri += "/index.html";
  return request;
}`),
    });

    const securityHeaders = new cloudfront.ResponseHeadersPolicy(this, "SecurityHeaders", {
      securityHeadersBehavior: {
        contentSecurityPolicy: {
          override: true,
          contentSecurityPolicy: "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; img-src 'self' data:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' https://api.incaof.com https://*.auth.us-east-1.amazoncognito.com; form-action 'self' https://*.auth.us-east-1.amazoncognito.com; upgrade-insecure-requests",
        },
        contentTypeOptions: { override: true },
        frameOptions: { frameOption: cloudfront.HeadersFrameOption.DENY, override: true },
        referrerPolicy: { referrerPolicy: cloudfront.HeadersReferrerPolicy.NO_REFERRER, override: true },
        strictTransportSecurity: {
          accessControlMaxAge: Duration.days(365),
          includeSubdomains: true,
          preload: true,
          override: true,
        },
        xssProtection: { protection: true, modeBlock: true, override: true },
      },
      customHeadersBehavior: {
        customHeaders: [
          { header: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()", override: true },
          { header: "Cross-Origin-Opener-Policy", value: "same-origin", override: true },
        ],
      },
    });

    const webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
      defaultAction: { allow: {} },
      scope: "CLOUDFRONT",
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: `ico-${props.environment.name}-web`,
        sampledRequestsEnabled: true,
      },
      rules: [
        {
          name: "rate-limit",
          priority: 1,
          action: { block: {} },
          statement: { rateBasedStatement: { aggregateKeyType: "IP", limit: 600 } },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `ico-${props.environment.name}-rate-limit`,
            sampledRequestsEnabled: true,
          },
        },
        {
          name: "aws-common-rules",
          priority: 2,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: { vendorName: "AWS", name: "AWSManagedRulesCommonRuleSet" },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `ico-${props.environment.name}-common-rules`,
            sampledRequestsEnabled: true,
          },
        },
      ],
    });

    const functionAssociations = [{
      function: rewrite,
      eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
    }];
    const marketingOrigin = origins.S3BucketOrigin.withOriginAccessControl(this.marketingBucket);
    const responderOrigin = origins.S3BucketOrigin.withOriginAccessControl(this.responderBucket);
    const behavior = (origin: cloudfront.IOrigin): cloudfront.BehaviorOptions => ({
      origin,
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
      cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      compress: true,
      functionAssociations,
      responseHeadersPolicy: securityHeaders,
    });

    this.distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultRootObject: "index.html",
      defaultBehavior: behavior(marketingOrigin),
      additionalBehaviors: {
        "r/*": behavior(responderOrigin),
        "i/*": behavior(responderOrigin),
        "runtime-config.json": {
          ...behavior(marketingOrigin),
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        },
      },
      domainNames: certificate ? ["incaof.com", "www.incaof.com"] : undefined,
      certificate,
      webAclId: webAcl.attrArn,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      enableIpv6: true,
    });

    if (zone && certificate) {
      for (const recordName of [undefined, "www"]) {
        new route53.ARecord(this, recordName ? "WwwAlias" : "ApexAlias", {
          zone,
          recordName,
          target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(this.distribution)),
        });
      }
      const reusingApiDomain = Boolean(
        props.existingApiDomainRegionalName && props.existingApiDomainHostedZoneId,
      );
      const apiDomain = reusingApiDomain
        ? apigw.DomainName.fromDomainNameAttributes(this, "ExistingApiDomain", {
            name: "api.incaof.com",
            regionalDomainName: props.existingApiDomainRegionalName!,
            regionalHostedZoneId: props.existingApiDomainHostedZoneId!,
          })
        : new apigw.DomainName(this, "ApiDomain", {
            domainName: "api.incaof.com",
            certificate,
          });
      new apigw.ApiMapping(this, "ApiMapping", { api: props.httpApi, domainName: apiDomain });
      if (!reusingApiDomain) {
        new route53.ARecord(this, "ApiAlias", {
          zone,
          recordName: "api",
          target: route53.RecordTarget.fromAlias(
            new targets.ApiGatewayv2DomainProperties(apiDomain.regionalDomainName, apiDomain.regionalHostedZoneId),
          ),
        });
      }
    }

    new CfnOutput(Stack.of(this), "WebsiteUrl", {
      value: certificate ? "https://incaof.com" : `https://${this.distribution.distributionDomainName}`,
    });
    new CfnOutput(Stack.of(this), "MarketingBucketName", { value: this.marketingBucket.bucketName });
    new CfnOutput(Stack.of(this), "ResponderBucketName", { value: this.responderBucket.bucketName });
    new CfnOutput(Stack.of(this), "DistributionId", { value: this.distribution.distributionId });
  }
}
