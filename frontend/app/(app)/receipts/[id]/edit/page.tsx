import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { receiptsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={receiptsModule} />;
}
